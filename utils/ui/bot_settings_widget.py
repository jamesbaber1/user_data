from PySide2 import QtCore, QtGui, QtWidgets


class BotWidget(QtWidgets.QWidget):
    """
    Custom Qt Widget to show a power bar and dial.
    Demonstrating compound and custom-drawn widget.
    """

    def __init__(self, steps=5, *args, **kwargs):
        super(BotWidget, self).__init__(*args, **kwargs)

        layout = QtWidgets.QHBoxLayout()

        self._check_box = QtWidgets.QCheckBox('update')
        layout.addWidget(self._check_box)

        self._check_box = QtWidgets.QCheckBox('full reset')
        layout.addWidget(self._check_box)

        self._check_box = QtWidgets.QCheckBox('dry run')
        layout.addWidget(self._check_box)

        self.setLayout(layout)