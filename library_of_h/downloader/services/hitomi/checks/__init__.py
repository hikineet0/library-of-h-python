# from . import check

# def main():
#     for attr in check.__all__:
#         CustomIO.print(
#             f"\rChecking for \"{attr.replace('check_', '')}\"...",
#             end='', carriage_return=True
#         )
#         CustomIO.print(
#                     f"\rCheck for \"{attr.replace('check_', '')}\": ",
#                     ["Failed.", "Successful."][getattr(check, attr)()],
#                     carriage_return=True
#         )

#     CustomIO.print()

if __name__ == "__main__":
    main()
