from PySide2 import QtCore, QtGui, QtUiTools, QtWidgets
from ui.bot_settings_widget import BotWidget


def loadUiWidget(uifilename, parent=None):
    loader = QtUiTools.QUiLoader()
    uifile = QtCore.QFile(uifilename)
    uifile.open(QtCore.QFile.ReadOnly)
    ui = loader.load(uifile, parent)
    uifile.close()
    return ui


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = loadUiWidget("/home/unbuntu/Documents/python_projects/freqtrade/user_data/utils/ui/bot_manager.ui")
    bot_widget = loadUiWidget("/home/unbuntu/Documents/python_projects/freqtrade/user_data/utils/ui/bot_widget.ui")

    # MainWindow.bot_list.addScrollBarWidget = True
    # MainWindow.bot_list.setAlternatingRowColors(True)
    # MainWindow.bot_list.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)

    # layout = QtWidgets.QBoxLayout()
    # button = QtWidgets.QPushButton()
    # button.text = 'Jamesy'

    widget = QtWidgets.QWidget()
    vbox = QtWidgets.QVBoxLayout()

    for i in range(1, 20):
        bot_widget = BotWidget()
        vbox.addWidget(bot_widget)

    widget.setLayout(vbox)
    MainWindow.scroll_area.setWidget(widget)


    # for i in dir(MainWindow.scroll_area_layout):
    #     print(i)
    # # MainWindow.scroll_area
    # MainWindow.scroll_area.setWidget(bot_widget)

    MainWindow.show()
    sys.exit(app.exec_())