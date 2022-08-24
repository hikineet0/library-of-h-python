from PySide6 import QtCore as qtc


class MoveToTrashWorker(qtc.QObject):

    trash_batch_finished_signal = qtc.Signal(list)
    item_trash_finished_signal = qtc.Signal(str)
    item_trash_started_signal = qtc.Signal(str)

    def __init__(self, parent: qtc.QObject, directory_paths: tuple[str, ...]):
        super().__init__(parent=parent)
        self._directory_paths = directory_paths

    def move_to_trash(self):
        faulty_directories = []
        for directory_path in self._directory_paths:
            self.item_trash_started_signal.emit(directory_path)

            if self.parent().wasCanceled():
                break

            if not qtc.QFile.moveToTrash(directory_path):
                faulty_directories.append(qtc.QDir(directory_path).filePath(item_name))

            self.item_trash_finished_signal.emit(directory_path)

        self.trash_batch_finished_signal.emit(faulty_directories)
