from collections.abc import Callable

from PySide6 import QtWidgets


def createButton(buttonName: str, layout, click_fun:Callable):
    button: QtWidgets.QPushButton = QtWidgets.QPushButton(buttonName)
    if Callable is not None:
        button.clicked.connect(click_fun)
    layout.addWidget(button)