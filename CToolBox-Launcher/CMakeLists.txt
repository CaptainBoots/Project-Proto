cmake_minimum_required(VERSION 3.16)

# ==============================================================================
# CToolBox-Launcher Version Configuration
# Set the version string manually here (independent of the Python version)
# ==============================================================================
set(LAUNCHER_VERSION "1.1.1")

project(CToolBox-Launcher VERSION ${LAUNCHER_VERSION} LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

# Find Qt6 modules
find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets Network)

# Pass the dynamic version to the C++ compiler as a preprocessor definition with escaped quotes
add_compile_definitions(APP_VERSION=\"${PROJECT_VERSION}\")

add_executable(CToolBox-Launcher
    src/main.cpp
    src/mainwindow.h
    src/mainwindow.cpp
    src/onboardingwizard.h
    src/onboardingwizard.cpp
    src/settingsdialog.h
    src/settingsdialog.cpp
    src/helpdialog.h
    src/helpdialog.cpp
    src/configmanager.h
    src/configmanager.cpp
    src/customwidgets.h
    src/customwidgets.cpp
    src/theme.h
    src/theme.cpp
)

target_link_libraries(CToolBox-Launcher PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::Widgets
    Qt6::Network
)

# Add Uninstaller executable
add_executable(CToolBox-Uninstaller
    src/uninstaller.cpp
)

target_link_libraries(CToolBox-Uninstaller PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::Widgets
)

# On Windows, build as a windowed application (hides the console window)
if(WIN32)
    set_target_properties(CToolBox-Launcher PROPERTIES WIN32_EXECUTABLE TRUE)
    set_target_properties(CToolBox-Uninstaller PROPERTIES WIN32_EXECUTABLE TRUE)
endif()
