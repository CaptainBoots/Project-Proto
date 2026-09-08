#include "settingsdialog.h"
#include "theme.h"
#include "configmanager.h"
#include "customwidgets.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QFrame>
#include <QFileDialog>
#include <QMessageBox>
#include <QFontMetrics>
#include <QScrollArea>
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QProcess>
#include <QMouseEvent>

SettingsDialog::SettingsDialog(QWidget* parent) : QDialog(parent), m_themesOpen(false) {
    setWindowTitle("Settings");
    resize(520, 560);
    ThemePalette p = ThemeManager::instance().currentPalette();
    setStyleSheet(QString("background-color: %1;").arg(p.bg));

    QVBoxLayout* rootLayout = new QVBoxLayout(this);
    rootLayout->setContentsMargins(0, 0, 0, 0);
    rootLayout->setSpacing(0);

    // ── Header ────────────────────────────────────────────────────────────
    QWidget* header = new QWidget();
    header->setStyleSheet(QString("background-color: %1;").arg(p.panel));
    QHBoxLayout* headerLayout = new QHBoxLayout(header);
    headerLayout->setContentsMargins(20, 10, 20, 10);
    QLabel* titleLabel = new QLabel(QString("Manage Scripts & Settings (v%1)").arg(ConfigManager::instance().version()));
    titleLabel->setStyleSheet(QString("color: %1; background: transparent; border: none;").arg(p.accent2));
    titleLabel->setFont(ThemeManager::instance().qtFont(12, true));
    headerLayout->addWidget(titleLabel);
    rootLayout->addWidget(header);

    QFrame* divider = new QFrame();
    divider->setFixedHeight(1);
    divider->setStyleSheet(QString("background-color: %1; border: none;").arg(p.border));
    rootLayout->addWidget(divider);

    // ── Scrollable Body ───────────────────────────────────────────────────
    QScrollArea* outerScroll = new QScrollArea();
    outerScroll->setWidgetResizable(true);
    outerScroll->setStyleSheet(QString("background-color: %1; border: none;").arg(p.bg));

    QWidget* body = new QWidget();
    body->setStyleSheet(QString("background-color: %1;").arg(p.bg));
    QVBoxLayout* bodyLayout = new QVBoxLayout(body);
    bodyLayout->setContentsMargins(20, 14, 20, 14);
    bodyLayout->setSpacing(10);
    outerScroll->setWidget(body);
    rootLayout->addWidget(outerScroll, 1);

    // ── Branch Selection ──────────────────────────────────────────────────
    QHBoxLayout* branchRow = new QHBoxLayout();
    QLabel* branchLbl = new QLabel("Update Branch Context:");
    branchLbl->setStyleSheet(QString("color: %1; background: transparent; border: none;").arg(p.text));
    branchLbl->setFont(ThemeManager::instance().qtFont(9, true));
    branchRow->addWidget(branchLbl);

    m_branchCombo = new QComboBox();
    m_branchCombo->addItems({"main", "beta"});
    m_branchCombo->setCurrentText(ConfigManager::instance().updateBranch());
    m_branchCombo->setFont(ThemeManager::instance().qtFont(9));
    m_branchCombo->setCursor(Qt::PointingHandCursor);
    connect(m_branchCombo, &QComboBox::currentTextChanged, this, &SettingsDialog::changeBranch);
    branchRow->addWidget(m_branchCombo);
    branchRow->addStretch(1);
    bodyLayout->addLayout(branchRow);

    // ── Python Interpreter ────────────────────────────────────────────────
    QHBoxLayout* pythonRow = new QHBoxLayout();
    QLabel* pythonLbl = new QLabel("Python Interpreter:");
    pythonLbl->setStyleSheet(QString("color: %1; background: transparent; border: none;").arg(p.text));
    pythonLbl->setFont(ThemeManager::instance().qtFont(9, true));
    pythonRow->addWidget(pythonLbl);

    QString defaultPython = ConfigManager::instance().pythonInterpreter();
    m_pythonEntry = new QLineEdit(defaultPython.isEmpty() ? "Default / Auto-Discovered" : defaultPython);
    m_pythonEntry->setReadOnly(true);
    m_pythonEntry->setFont(ThemeManager::instance().qtFont(8));
    m_pythonEntry->setStyleSheet(ThemeManager::instance().lineEditQss());
    pythonRow->addWidget(m_pythonEntry, 1);

    QPushButton* browsePythonBtn = new QPushButton("Browse...");
    browsePythonBtn->setStyleSheet(ThemeManager::instance().subtleButtonQss());
    browsePythonBtn->setFont(ThemeManager::instance().qtFont(8, true));
    browsePythonBtn->setCursor(Qt::PointingHandCursor);
    connect(browsePythonBtn, &QPushButton::clicked, this, &SettingsDialog::browsePython);
    pythonRow->addWidget(browsePythonBtn);

    QPushButton* resetPythonBtn = new QPushButton("Reset");
    resetPythonBtn->setStyleSheet(ThemeManager::instance().subtleButtonQss());
    resetPythonBtn->setFont(ThemeManager::instance().qtFont(8, true));
    resetPythonBtn->setCursor(Qt::PointingHandCursor);
    connect(resetPythonBtn, &QPushButton::clicked, this, &SettingsDialog::resetPython);
    pythonRow->addWidget(resetPythonBtn);

    bodyLayout->addLayout(pythonRow);

    // ── Tools Installation Folder ─────────────────────────────────────────
    QHBoxLayout* toolsRow = new QHBoxLayout();
    QLabel* toolsLbl = new QLabel("Tools Folder:");
    toolsLbl->setStyleSheet(QString("color: %1; background: transparent; border: none;").arg(p.text));
    toolsLbl->setFont(ThemeManager::instance().qtFont(9, true));
    toolsRow->addWidget(toolsLbl);

    m_toolsEntry = new QLineEdit(ConfigManager::instance().toolsRootDir());
    m_toolsEntry->setReadOnly(true);
    m_toolsEntry->setFont(ThemeManager::instance().qtFont(8));
    m_toolsEntry->setStyleSheet(ThemeManager::instance().lineEditQss());
    toolsRow->addWidget(m_toolsEntry, 1);

    QPushButton* changeToolsBtn = new QPushButton("Change...");
    changeToolsBtn->setStyleSheet(ThemeManager::instance().subtleButtonQss());
    changeToolsBtn->setFont(ThemeManager::instance().qtFont(8, true));
    changeToolsBtn->setCursor(Qt::PointingHandCursor);
    connect(changeToolsBtn, &QPushButton::clicked, this, &SettingsDialog::changeToolsFolder);
    toolsRow->addWidget(changeToolsBtn);

    bodyLayout->addLayout(toolsRow);

    // ── Themes Collapsible ────────────────────────────────────────────────
    QWidget* themeHeader = new QWidget();
    themeHeader->setCursor(Qt::PointingHandCursor);
    QHBoxLayout* themeHeaderLayout = new QHBoxLayout(themeHeader);
    themeHeaderLayout->setContentsMargins(0, 8, 0, 0);

    m_themeArrow = new QLabel("▶");
    m_themeArrow->setStyleSheet(QString("color: %1; background: transparent; border: none;").arg(p.accent2));
    m_themeArrow->setFont(ThemeManager::instance().qtFont(12, true));
    themeHeaderLayout->addWidget(m_themeArrow);

    QLabel* themesLbl = new QLabel("  Themes");
    themesLbl->setStyleSheet(QString("color: %1; background: transparent; border: none;").arg(p.accent2));
    themesLbl->setFont(ThemeManager::instance().qtFont(12, true));
    themeHeaderLayout->addWidget(themesLbl);

    m_themePreview = new QLabel(QString("(%1)").arg(ThemeManager::instance().labels()[ThemeManager::instance().currentMode()]));
    m_themePreview->setStyleSheet(QString("color: %1; background: transparent; border: none;").arg(p.subtext));
    m_themePreview->setFont(ThemeManager::instance().qtFont(9));
    themeHeaderLayout->addWidget(m_themePreview);
    themeHeaderLayout->addStretch(1);

    bodyLayout->addWidget(themeHeader);

    m_themeRestartLbl = new QLabel("Applies immediately");
    m_themeRestartLbl->setStyleSheet(QString("color: %1; background: transparent; border: none;").arg(p.subtext));
    m_themeRestartLbl->setFont(ThemeManager::instance().qtFont(8));
    bodyLayout->addWidget(m_themeRestartLbl);
    m_themeRestartLbl->hide();

    m_themeBody = new QWidget();
    QVBoxLayout* themeBodyLayout = new QVBoxLayout(m_themeBody);
    themeBodyLayout->setContentsMargins(20, 4, 0, 0);
    bodyLayout->addWidget(m_themeBody);
    m_themeBody->hide();

    // Fill themes
    QMap<QString, QString> themeLabels = ThemeManager::instance().labels();
    QMap<QString, ThemePalette> themePalettes = ThemeManager::instance().palettes();
    
    // Add rows
    for (auto it = themeLabels.begin(); it != themeLabels.end(); ++it) {
        QString mode = it.key();
        QString labelText = it.value();
        ThemePalette tp = themePalettes[mode];

        QWidget* row = new QWidget();
        row->setCursor(Qt::PointingHandCursor);
        QHBoxLayout* rowLayout = new QHBoxLayout(row);
        rowLayout->setContentsMargins(0, 3, 0, 3);

        CircleToggle* toggle = new CircleToggle(row, (mode == ThemeManager::instance().currentMode()), tp.accent);
        rowLayout->addWidget(toggle);

        QLabel* lbl = new QLabel(labelText);
        lbl->setFont(ThemeManager::instance().qtFont(9));
        lbl->setStyleSheet(QString("color: %1; background: transparent; border: none;")
                           .arg(mode == ThemeManager::instance().currentMode() ? tp.accent2 : tp.text));
        rowLayout->addWidget(lbl);

        QWidget* swatch = new QWidget();
        QHBoxLayout* swatchLayout = new QHBoxLayout(swatch);
        swatchLayout->setContentsMargins(4, 0, 0, 0);
        swatchLayout->setSpacing(1);

        QStringList swatchColors = {tp.bg, tp.panel, tp.accent, tp.accent2};
        for (const QString& clr : swatchColors) {
            QFrame* sw = new QFrame();
            sw->setFixedSize(14, 14);
            sw->setStyleSheet(QString("background-color: %1; border: 1px solid %2;").arg(clr, p.border));
            swatchLayout->addWidget(sw);
        }
        rowLayout->addWidget(swatch);
        rowLayout->addStretch(1);

        row->setProperty("theme_mode", mode);
        row->setProperty("toggle_ptr", QVariant::fromValue(static_cast<void*>(toggle)));
        row->setProperty("label_ptr", QVariant::fromValue(static_cast<void*>(lbl)));

        // Click handler
        row->installEventFilter(this); // Filter to capture press, or subclass widget
        // Instead of event filter, let's connect CircleToggle's signal and use simple click
        connect(toggle, &CircleToggle::toggled, this, [this, mode]() {
            selectTheme(mode);
        });

        themeBodyLayout->addWidget(row);
    }

    // Toggle theme click
    // We can filter mouse clicks on themeHeader or use a button style. Let's make it a button-like interaction.
    themeHeader->installEventFilter(this);

    // ── Managed Scripts List ──────────────────────────────────────────────
    QLabel* scriptsLbl = new QLabel("Managed Scripts");
    scriptsLbl->setStyleSheet(QString("color: %1; background: transparent; border: none;").arg(p.accent2));
    scriptsLbl->setFont(ThemeManager::instance().qtFont(10, true));
    bodyLayout->addWidget(scriptsLbl);

    QFrame* listPanel = new QFrame();
    listPanel->setStyleSheet(QString("background-color: %1; border: 1px solid %2;").arg(p.panel, p.border));
    listPanel->setMinimumHeight(200);
    QVBoxLayout* listPanelLayout = new QVBoxLayout(listPanel);
    listPanelLayout->setContentsMargins(0, 4, 0, 4);

    QScrollArea* listScroll = new QScrollArea();
    listScroll->setWidgetResizable(true);
    listScroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
    listScroll->setStyleSheet(QString("background-color: %1; border: none;").arg(p.panel));

    QWidget* listInner = new QWidget();
    listInner->setStyleSheet(QString("background-color: %1;").arg(p.panel));
    m_scriptListLayout = new QVBoxLayout(listInner);
    m_scriptListLayout->setContentsMargins(0, 0, 0, 0);
    m_scriptListLayout->setSpacing(0);
    
    listScroll->setWidget(listInner);
    listPanelLayout->addWidget(listScroll);
    bodyLayout->addWidget(listPanel, 1);

    // ── Bottom Action Row ─────────────────────────────────────────────────
    QFrame* navFrame = new QFrame();
    navFrame->setStyleSheet(QString("background-color: %1;").arg(p.bg));
    QHBoxLayout* navLayout = new QHBoxLayout(navFrame);
    navLayout->setContentsMargins(20, 8, 20, 14);

    QPushButton* addBtn = new QPushButton("+ Add Script");
    addBtn->setStyleSheet(ThemeManager::instance().accentButtonQss());
    addBtn->setFont(ThemeManager::instance().qtFont(9, true));
    addBtn->setCursor(Qt::PointingHandCursor);
    addBtn->setMinimumWidth(120);
    connect(addBtn, &QPushButton::clicked, this, &SettingsDialog::addScript);
    navLayout->addWidget(addBtn);

    navLayout->addStretch(1);

    QPushButton* consoleBtn = new QPushButton("Console Log");
    consoleBtn->setStyleSheet(ThemeManager::instance().subtleButtonQss());
    consoleBtn->setFont(ThemeManager::instance().qtFont(9, true));
    consoleBtn->setCursor(Qt::PointingHandCursor);
    consoleBtn->setMinimumWidth(110);
    connect(consoleBtn, &QPushButton::clicked, this, &SettingsDialog::openConsole);
    navLayout->addWidget(consoleBtn);

    QPushButton* closeBtn = new QPushButton("Close");
    closeBtn->setStyleSheet(ThemeManager::instance().subtleButtonQss());
    closeBtn->setFont(ThemeManager::instance().qtFont(9, true));
    closeBtn->setCursor(Qt::PointingHandCursor);
    closeBtn->setMinimumWidth(90);
    connect(closeBtn, &QPushButton::clicked, this, &SettingsDialog::close);
    navLayout->addWidget(closeBtn);

    rootLayout->addWidget(navFrame);

    refreshScriptList();
}

void SettingsDialog::changeBranch(const QString& newBranch) {
    if (newBranch == ConfigManager::instance().updateBranch()) return;
    ConfigManager::instance().setUpdateBranch(newBranch);
    ConfigManager::instance().save();
}

void SettingsDialog::browsePython() {
    QString chosen = QFileDialog::getOpenFileName(this, "Select Python Interpreter", "", 
#ifdef Q_OS_WIN
        "Python executable (*.exe)"
#else
        "All files (*)"
#endif
    );
    if (!chosen.isEmpty()) {
        ConfigManager::instance().setPythonInterpreter(QDir::toNativeSeparators(chosen));
        m_pythonEntry->setText(ConfigManager::instance().pythonInterpreter());
        ConfigManager::instance().save();
    }
}

void SettingsDialog::resetPython() {
    ConfigManager::instance().setPythonInterpreter("");
    m_pythonEntry->setText("Default / Auto-Discovered");
    ConfigManager::instance().save();
}

void SettingsDialog::changeToolsFolder() {
    QString chosen = QFileDialog::getExistingDirectory(this, "Select Nova-Tools Installation Folder", ConfigManager::instance().toolsRootDir());
    if (chosen.isEmpty() || chosen == ConfigManager::instance().toolsRootDir()) return;

    QString oldDir = ConfigManager::instance().toolsRootDir();
    QString newDir = QDir::toNativeSeparators(chosen);

    // If there are files in old directory, prompt to copy
    QDir oldQDir(oldDir);
    if (oldQDir.exists() && !oldQDir.entryList(QDir::Files | QDir::Dirs | QDir::NoDotAndDotDot).isEmpty()) {
        auto ans = QMessageBox::question(this, "Move Existing Tools?",
            QString("Would you like to move your existing Nova-Tools files from:\n%1\n\nto the new directory:\n%2?")
            .arg(oldDir, newDir), QMessageBox::Yes | QMessageBox::No | QMessageBox::Cancel);
        
        if (ans == QMessageBox::Cancel) {
            return;
        } else if (ans == QMessageBox::Yes) {
            // Helper function to recursively copy files in C++ (or let's run simple copy commands, or QDir recursively)
            // Let's do a simple folder copy via standard platform command or Qt code.
            // In Windows: robocopy "src" "dst" /E
            // In others: cp -r "src" "dst"
#ifdef Q_OS_WIN
            QStringList args = {oldDir, newDir, "/E", "/MOVE", "/XD", "configs", "ToolBox Backup"};
            QProcess::execute("robocopy", args);
#else
            // cp -r
            QStringList args = {"-r", oldDir + "/.", newDir};
            QProcess::execute("cp", args);
#endif
        }
    }

    ConfigManager::instance().setToolsRootDir(newDir);
    m_toolsEntry->setText(ConfigManager::instance().toolsRootDir());
    
    // Save central pointer
    QFile ptrFile(ConfigManager::instance().toolsPathPointerFile());
    if (ptrFile.open(QIODevice::WriteOnly | QIODevice::Text)) {
        QTextStream out(&ptrFile);
        out << newDir;
        ptrFile.close();
    }

    ConfigManager::instance().save();
    emit scriptsChanged();
    refreshScriptList();
}

void SettingsDialog::toggleThemes() {
    m_themesOpen = !m_themesOpen;
    if (m_themesOpen) {
        m_themeArrow->setText("▼");
        m_themeRestartLbl->show();
        m_themeBody->show();
    } else {
        m_themeArrow->setText("▶");
        m_themeRestartLbl->hide();
        m_themeBody->hide();
    }
}

void SettingsDialog::selectTheme(const QString& mode) {
    ThemeManager::instance().setTheme(mode);
    ConfigManager::instance().save();
    
    m_themePreview->setText(QString("(%1)").arg(ThemeManager::instance().labels()[mode]));
    
    // Update label styles and toggles inside the dialogue
    ThemePalette tp = ThemeManager::instance().currentPalette();
    QList<QWidget*> children = m_themeBody->findChildren<QWidget*>();
    for (QWidget* child : children) {
        QString childMode = child->property("theme_mode").toString();
        if (!childMode.isEmpty()) {
            CircleToggle* t = static_cast<CircleToggle*>(child->property("toggle_ptr").value<void*>());
            QLabel* l = static_cast<QLabel*>(child->property("label_ptr").value<void*>());
            if (t && l) {
                t->set(childMode == mode);
                l->setStyleSheet(QString("color: %1; background: transparent; border: none;")
                                 .arg(childMode == mode ? tp.accent2 : tp.text));
            }
        }
    }

    emit themeChanged(mode);
}

void SettingsDialog::refreshScriptList() {
    // Clear list
    QLayoutItem* item;
    while ((item = m_scriptListLayout->takeAt(0)) != nullptr) {
        delete item->widget();
        delete item;
    }

    QVector<ManagedScript> scripts = ConfigManager::instance().managedScripts();
    ThemePalette p = ThemeManager::instance().currentPalette();

    for (int i = 0; i < scripts.size(); ++i) {
        ManagedScript script = scripts[i];

        QWidget* scriptRow = new QWidget();
        scriptRow->setStyleSheet(QString("background-color: %1;").arg(p.bg));
        QHBoxLayout* rowLayout = new QHBoxLayout(scriptRow);
        rowLayout->setContentsMargins(10, 6, 10, 6);

        QLabel* nameLbl = new QLabel(script.label);
        nameLbl->setStyleSheet(QString("color: %1; background: transparent; border: none;").arg(p.text));
        nameLbl->setFont(ThemeManager::instance().qtFont(9, true));
        rowLayout->addWidget(nameLbl);
        rowLayout->addStretch(1);

        QFont fileFont = ThemeManager::instance().qtFont(8);
        QFontMetrics fileMetrics(fileFont);
        QString elided = fileMetrics.elidedText(QString("(%1)").arg(script.filename), Qt::ElideMiddle, 170);
        
        QLabel* fileLbl = new QLabel(elided);
        fileLbl->setToolTip(script.filename);
        fileLbl->setFixedWidth(170);
        fileLbl->setAlignment(Qt::AlignRight | Qt::AlignVCenter);
        fileLbl->setStyleSheet(QString("color: %1; background: transparent; border: none;").arg(p.subtext));
        fileLbl->setFont(fileFont);
        rowLayout->addWidget(fileLbl);

        if (script.custom) {
            QPushButton* removeBtn = new QPushButton("✕ Remove");
            removeBtn->setStyleSheet(
                QString("QPushButton { background-color: %1; color: %2; border: none; border-radius: 3px; padding: 3px 10px; font-weight: bold; }"
                        "QPushButton:hover { background-color: %3; }")
                .arg(p.panel, p.red, p.border)
            );
            removeBtn->setFont(ThemeManager::instance().qtFont(8, true));
            removeBtn->setCursor(Qt::PointingHandCursor);
            connect(removeBtn, &QPushButton::clicked, this, [this, i]() { removeScript(i); });
            rowLayout->addWidget(removeBtn);
        } else {
            QLabel* coreLbl = new QLabel("🔒 Core Tool");
            coreLbl->setStyleSheet(QString("color: %1; background: transparent; border: none; padding-right: 5px;").arg(p.subtext));
            coreLbl->setFont(ThemeManager::instance().qtFont(8, true));
            rowLayout->addWidget(coreLbl);
        }

        m_scriptListLayout->addWidget(scriptRow);

        QFrame* rowDivider = new QFrame();
        rowDivider->setFixedHeight(1);
        rowDivider->setStyleSheet(QString("background-color: %1; border: none;").arg(p.border));
        m_scriptListLayout->addWidget(rowDivider);
    }

    m_scriptListLayout->addStretch(1);
}

void SettingsDialog::removeScript(int idx) {
    ConfigManager::instance().removeManagedScript(idx);
    ConfigManager::instance().save();
    refreshScriptList();
    emit scriptsChanged();
}

void SettingsDialog::addScript() {
    QDialog addWin(this);
    addWin.setWindowTitle("Add Script");
    addWin.setFixedSize(400, 200);
    ThemePalette p = ThemeManager::instance().currentPalette();
    addWin.setStyleSheet(QString("background-color: %1;").arg(p.bg));

    QGridLayout* grid = new QGridLayout(&addWin);
    grid->setContentsMargins(14, 14, 14, 14);
    grid->setVerticalSpacing(10);

    QLabel* labelCaption = new QLabel("Script Display Label:");
    labelCaption->setStyleSheet(QString("color: %1; background: transparent; border: none;").arg(p.text));
    labelCaption->setFont(ThemeManager::instance().qtFont(9));
    grid->addWidget(labelCaption, 0, 0);

    QLineEdit* labelEntry = new QLineEdit();
    labelEntry->setFont(ThemeManager::instance().qtFont(9));
    labelEntry->setStyleSheet(ThemeManager::instance().lineEditQss());
    grid->addWidget(labelEntry, 0, 1);

    QLabel* fileCaption = new QLabel("Filename / Resource Path:");
    fileCaption->setStyleSheet(QString("color: %1; background: transparent; border: none;").arg(p.text));
    fileCaption->setFont(ThemeManager::instance().qtFont(9));
    grid->addWidget(fileCaption, 1, 0);

    QLineEdit* fileEntry = new QLineEdit();
    fileEntry->setFont(ThemeManager::instance().qtFont(9));
    fileEntry->setStyleSheet(ThemeManager::instance().lineEditQss());
    grid->addWidget(fileEntry, 1, 1);

    QPushButton* submitBtn = new QPushButton("Save Script");
    submitBtn->setStyleSheet(ThemeManager::instance().accentButtonQss());
    submitBtn->setFont(ThemeManager::instance().qtFont(9, true));
    submitBtn->setCursor(Qt::PointingHandCursor);
    grid->addWidget(submitBtn, 2, 1, Qt::AlignRight);

    connect(submitBtn, &QPushButton::clicked, &addWin, [&]() {
        QString lbl = labelEntry->text().trimmed();
        QString flm = fileEntry->text().trimmed();
        if (lbl.isEmpty() || flm.isEmpty()) {
            QMessageBox::warning(&addWin, "Validation Error", "All entry parameters must be populated.");
            return;
        }

        ManagedScript s;
        s.label = lbl;
        s.filename = flm;
        s.custom = true;
        ConfigManager::instance().addManagedScript(s);
        ConfigManager::instance().save();
        
        refreshScriptList();
        emit scriptsChanged();
        addWin.accept();
    });

    grid->setColumnStretch(1, 1);
    addWin.exec();
}

void SettingsDialog::openConsole() {
    ConsoleWindow* console = new ConsoleWindow(this);
    console->setWindowModality(Qt::NonModal);
    console->show();
}

// Intercept click on the themeHeader
bool SettingsDialog::eventFilter(QObject* watched, QEvent* event) {
    if (event->type() == QEvent::MouseButtonPress) {
        QMouseEvent* mouseEvent = static_cast<QMouseEvent*>(event);
        if (mouseEvent->button() == Qt::LeftButton) {
            // Find if it was on our themeHeader
            QWidget* themeHeader = qobject_cast<QWidget*>(watched);
            if (themeHeader && themeHeader->layout() != nullptr) {
                toggleThemes();
                return true;
            }
        }
    }
    return QDialog::eventFilter(watched, event);
}
