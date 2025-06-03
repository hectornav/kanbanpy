from setuptools import setup, find_packages

setup(
    name="kanban-app",
    version="1.0",
    packages=find_packages(),
    install_requires=['PyQt6'],
    entry_points={
        'console_scripts': [
            'kanban=main:main',
        ],
    },
    data_files=[
        ('share/applications', ['assets/kanban.desktop']),
        ('share/icons', ['assets/kanban.png']),
        ('share/kanban-app', ['kanban_data.json']),
    ],
    include_package_data=True,
)