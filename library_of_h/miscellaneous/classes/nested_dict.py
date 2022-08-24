from typing import (Any, Dict, Generic, Hashable, Iterable, Iterator, Mapping,
                    MutableMapping, Optional, Tuple, TypeVar, Union)

KT = TypeVar("KT", bound=Hashable)
VT = TypeVar("VT")
Self = TypeVar("Self", bound="NestedDict")

NestedDictType = Dict[
    KT,
    Union[
        VT,
        Dict[
            KT,
            Union[
                VT,
                Dict[
                    KT,
                    Union[
                        VT,
                        Dict[
                            KT,
                            Any,
                        ],
                    ],
                ],
            ],
        ],
    ],
]

NestedMappingType = Mapping[
    KT,
    Union[
        VT,
        Mapping[
            KT,
            Union[
                VT,
                Mapping[
                    KT,
                    Union[
                        VT,
                        Mapping[
                            KT,
                            Any,
                        ],
                    ],
                ],
            ],
        ],
    ],
]


class NestedDict(MutableMapping[KT, VT], Generic[KT, VT]):
    _dict: NestedDictType[KT, VT]

    __slots__ = ("_dict",)

    def __init__(
        self: Self,
        mapping: Optional[
            Union[
                NestedMappingType[KT, VT],
                Iterable[Tuple[KT, Union[VT, NestedMappingType[KT, VT]]]],
            ]
        ] = None,
        /,
        **kwargs: Union[VT, NestedMappingType[KT, VT]],
    ) -> None:
        self._dict = {}
        if isinstance(mapping, Mapping):
            self.nested_update(mapping)
        elif isinstance(mapping, Iterable):
            try:
                self.nested_update(dict(mapping))
            except TypeError:
                raise TypeError(
                    f"NestedDict(...) expected a mapping, iterable of key-value pairs, or None, but got {mapping!r}"
                )
        elif mapping is not None:
            raise TypeError(
                f"NestedDict(...) expected a mapping, iterable of key-value pairs, or None, but got {mapping!r}"
            )
        self.nested_update(kwargs)

    def __delitem__(self: Self, keys: Union[KT, Tuple[KT, ...]]) -> None:
        if not isinstance(keys, tuple):
            keys = (keys,)
        elif keys == ():
            self.clear()
            return
        results = [self._dict]
        for key in keys[:-1]:
            results.append(results[-1].setdefault(key, {}))
            if not isinstance(results[-1], dict):
                raise KeyError(key)
        if keys[-1] in results[-1]:
            del results[-1][keys[-1]]
        for key, result in zip(keys[-2::-1], results[-2::-1]):
            if result[key] == {}:
                del result[key]

    def __getitem__(
        self: Self, keys: Union[KT, Tuple[KT, ...]]
    ) -> Union[VT, NestedDictType[KT, VT]]:
        if not isinstance(keys, tuple):
            keys = (keys,)
        result = self._dict
        for key in keys:
            if not isinstance(result, dict):
                raise KeyError(key)
            result = result.get(key)
        if result is None:
            raise KeyError(key)
        return result

    def __iter__(self: Self) -> Iterator[KT]:
        return iter(self._dict)

    def __len__(self: Self) -> int:
        return len(self._dict)

    def __repr__(self: Self) -> str:
        if len(self) == 0:
            return f"{type(self).__name__}()"
        else:
            return f"{type(self).__name__}({self._dict!r})"

    def __reversed__(self: Self) -> Iterator[KT]:
        return reversed(self._dict)

    def __setitem__(
        self: Self,
        keys: Union[KT, Tuple[KT, ...]],
        value: Union[VT, NestedDictType[KT, VT]],
    ) -> None:
        if not isinstance(keys, tuple):
            keys = (keys,)
        elif keys == () and isinstance(value, Mapping):
            self.clear()
            self._dict.update(value)
            return
        elif keys == ():
            raise TypeError(
                f"can only update the entire dict with another dict, got {value!r}"
            )
        result = self._dict
        for key in keys[:-1]:
            result = result.setdefault(key, {})
            if not isinstance(result, dict):
                raise KeyError(key)
        result[keys[-1]] = value

    def __sub__(self, nested_dict: "NestedDict") -> "NestedDict":
        if not isinstance(nested_dict, NestedDict):
            raise TypeError(
                f"can only get difference between two NestedDict, got {nested_dict!r}"
            )
        difference_dict = NestedDict()
        lhs_items = set(self.nested_items())
        rhs_items = set(nested_dict.nested_items())
        for key, value in lhs_items - rhs_items:
            difference_dict[key] = value
        return difference_dict

    def nested_items(self) -> list[tuple[tuple[str, ...], Any]]:
        nested_items = []
        keys = []
        # `iter` to have it be exhaustable, else it'd keep going forever.
        items = [iter(self._dict.items())]

        while len(items) > 0:
            has_items = False
            # Since elements in `items` are exhaustable, the following for loop
            # will not run for the same element more than once. Useful when
            # `del`eting the elements last to first.
            for k, v in items[-1]:
                has_items = True
                if isinstance(v, dict):
                    keys.append(k)
                    items.append(iter(v.items()))
                    break
                else:
                    nested_items.append(((*keys, k), v))
            if not has_items:
                try:
                    del keys[-1]
                except IndexError:
                    # `keys` has one less element than `items`, so `keys` will
                    # be empty by the time `items` is down to its last element.
                    pass
                del items[-1]

        return nested_items

    def clear(self: Self) -> None:
        self._dict.clear()

    def nested_update(self: Self, mapping: NestedMappingType[KT, VT]) -> None:
        if not isinstance(mapping, Mapping):
            raise TypeError(
                f"can only update the entire dict with another dict, got {mapping!r}"
            )
        chains = [()]
        items = [iter(mapping.items())]
        while len(chains) > 0:
            chain = chains[-1]
            try:
                key, value = next(items[-1])
            except StopIteration:
                del chains[-1]
                del items[-1]
                continue
            if isinstance(value, Mapping):
                chains.append((*chain, key))
                items.append(iter(value.items()))
            else:
                self[(*chain, key)] = value

    def nested_replace(self: Self, mapping: NestedMappingType[KT, VT]) -> None:
        """
        Takes a mapping and updates the values in `self` from `mapping` for only
        the keys that exist in self. Discards otherwise.
        """
        if not isinstance(mapping, Mapping):
            raise TypeError(
                f"can only replace dict values using another dict, got {mapping!r}"
            )
        chains = [()]
        items = [iter(mapping.items())]
        while len(chains) > 0:
            chain = chains[-1]
            try:
                key, value = next(items[-1])
            except StopIteration:
                del chains[-1]
                del items[-1]
                continue
            if isinstance(value, Mapping):
                chains.append((*chain, key))
                items.append(iter(value.items()))
            else:
                try:
                    # Check if (*chain, key) key(s) exists(exist) in self.
                    self[(*chain, key)]
                except KeyError:
                    # If not, do nothing,
                    return
                else:
                    # else replace/update the existing value.
                    if value != "":
                        self[(*chain, key)] = value
