#include "onboardingwizard.h"
#include "theme.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QFrame>
#include <QFileDialog>
#include <QStandardPaths>
#include <QDir>
#include <QIcon>
#include <QCoreApplication>

OnboardingWizard::OnboardingWizard(QWidget* parent) : QDialog(parent) {
    setWindowTitle("CToolBox-Launcher Setup Wizard");
    setFixedSize(550, 450);

    // Initial values
    m_toolsDir = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation);
    // Standard AppLocalDataLocation on Windows is C:/Users/username/AppData/Local/ProjectName/
    // Let's force it to end with CToolBox-Launcher
    if (!m_toolsDir.endsWith("CToolBox-Launcher", Qt::CaseInsensitive)) {
        m_toolsDir = QDir(QStandardPaths::writableLocation(QStandardPaths::GenericDataLocation)).filePath("CToolBox-Launcher");
    }
    m_toolsDir = QDir::toNativeSeparators(m_toolsDir);
    m_selectedTheme = "rich_purple";
    ThemeManager::instance().setTheme(m_selectedTheme);

    ThemePalette p = ThemeManager::instance().currentPalette();
    setStyleSheet(QString("background-color: %1; color: %2;").arg(p.bg, p.text));

    m_stack = new QStackedWidget();

    // ─────────────────────────────────────────────────────────────────────────
    // Page 1: Welcome
    // ─────────────────────────────────────────────────────────────────────────
    QWidget* page1 = new QWidget();
    QVBoxLayout* p1Layout = new QVBoxLayout(page1);
    p1Layout->setContentsMargins(30, 30, 30, 30);
    p1Layout->setSpacing(15);

    QLabel* p1Logo = new QLabel();
    // Try to load logo if exists
    QString iconPath = QDir(QCoreApplication::applicationDirPath()).filePath("Images/Boot's-ToolBox-256.ico");
    if (QFile::exists(iconPath)) {
        p1Logo->setPixmap(QIcon(iconPath).pixmap(96, 96));
    } else {
        // Fallback or search parent dir
        iconPath = QDir(QCoreApplication::applicationDirPath() + "/../Images/Boot's-ToolBox-256.ico").canonicalPath();
        if (QFile::exists(iconPath)) {
            p1Logo->setPixmap(QIcon(iconPath).pixmap(96, 96));
        }
    }
    p1Logo->setAlignment(Qt::AlignCenter);
    p1Layout->addWidget(p1Logo);

    QLabel* p1Title = new QLabel("Welcome to CToolBox-Launcher! ✨");
    p1Title->setFont(ThemeManager::instance().qtFont(14, true));
    p1Title->setStyleSheet(QString("color: %1; background: transparent; border: none;").arg(p.accent2));
    p1Title->setAlignment(Qt::AlignCenter);
    p1Layout->addWidget(p1Title);

    QLabel* p1Desc = new QLabel(
        "Hello! I'm Boots. I'm going to help you get your ToolBox set up in "
        "just a few simple steps so it's not scary or confusing at all! :3\n\n"
        "CToolBox-Launcher lets you easily download, run, and update all of your "
        "favorite companion tools from a single centralized dashboard."
    );
    p1Desc->setFont(ThemeManager::instance().qtFont(10));
    p1Desc->setWordWrap(true);
    p1Desc->setStyleSheet(QString("color: %1; background: transparent; border: none; line-height: 140%;").arg(p.text));
    p1Layout->addWidget(p1Desc);
    p1Layout->addStretch();

    // ─────────────────────────────────────────────────────────────────────────
    // Page 2: Installation Path
    // ─────────────────────────────────────────────────────────────────────────
    QWidget* page2 = new QWidget();
    QVBoxLayout* p2Layout = new QVBoxLayout(page2);
    p2Layout->setContentsMargins(30, 30, 30, 30);
    p2Layout->setSpacing(15);

    QLabel* p2Title = new QLabel("Choose Your Tools Folder 📁");
    p2Title->setFont(ThemeManager::instance().qtFont(14, true));
    p2Title->setStyleSheet(QString("color: %1; background: transparent; border: none;").arg(p.accent2));
    p2Layout->addWidget(p2Title);

    QLabel* p2Desc = new QLabel(
        "Every companion tool is lightweight and modular. We need to choose "
        "where on your system these tools will be downloaded and kept.\n\n"
        "We highly recommend using our safe, default local AppData folder:"
    );
    p2Desc->setFont(ThemeManager::instance().qtFont(10));
    p2Desc->setWordWrap(true);
    p2Desc->setStyleSheet("background: transparent; border: none;");
    p2Layout->addWidget(p2Desc);

    m_pathEntry = new QLineEdit(m_toolsDir);
    m_pathEntry->setReadOnly(true);
    m_pathEntry->setFont(ThemeManager::instance().qtFont(9));
    m_pathEntry->setStyleSheet(ThemeManager::instance().lineEditQss());
    p2Layout->addWidget(m_pathEntry);

    QHBoxLayout* p2BtnLayout = new QHBoxLayout();
    QPushButton* chooseBtn = new QPushButton("📂 Browse / Choose Folder...");
    chooseBtn->setStyleSheet(ThemeManager::instance().subtleButtonQss());
    chooseBtn->setFont(ThemeManager::instance().qtFont(9, true));
    chooseBtn->setCursor(Qt::PointingHandCursor);
    connect(chooseBtn, &QPushButton::clicked, this, &OnboardingWizard::browseFolder);
    p2BtnLayout->addWidget(chooseBtn);

    QPushButton* defaultBtn = new QPushButton("↺ Use Default Path");
    defaultBtn->setStyleSheet(ThemeManager::instance().subtleButtonQss());
    defaultBtn->setFont(ThemeManager::instance().qtFont(9, true));
    defaultBtn->setCursor(Qt::PointingHandCursor);
    connect(defaultBtn, &QPushButton::clicked, this, &OnboardingWizard::useDefaultPath);
    p2BtnLayout->addWidget(defaultBtn);
    p2BtnLayout->addStretch();
    p2Layout->addLayout(p2BtnLayout);
    p2Layout->addStretch();

    // ─────────────────────────────────────────────────────────────────────────
    // Page 3: Theme Selection
    // ─────────────────────────────────────────────────────────────────────────
    QWidget* page3 = new QWidget();
    QVBoxLayout* p3Layout = new QVBoxLayout(page3);
    p3Layout->setContentsMargins(30, 30, 30, 30);
    p3Layout->setSpacing(15);

    QLabel* p3Title = new QLabel("Pick Your Style 🎨");
    p3Title->setFont(ThemeManager::instance().qtFont(14, true));
    p3Title->setStyleSheet(QString("color: %1; background: transparent; border: none;").arg(p.accent2));
    p3Layout->addWidget(p3Title);

    QLabel* p3Desc = new QLabel(
        "Pick a default colour palette to style your ToolBox dashboard. "
        "You can always customize and change this anytime in Settings!"
    );
    p3Desc->setFont(ThemeManager::instance().qtFont(10));
    p3Desc->setWordWrap(true);
    p3Desc->setStyleSheet("background: transparent; border: none;");
    p3Layout->addWidget(p3Desc);

    m_themeCombo = new QComboBox();
    QMap<QString, QString> labels = ThemeManager::instance().labels();
    // Maintain insertion order by keys
    for (auto it = labels.begin(); it != labels.end(); ++it) {
        m_themeCombo->addItem(it.value(), it.key());
    }
    m_themeCombo->setCurrentText(labels[m_selectedTheme]);
    m_themeCombo->setFont(ThemeManager::instance().qtFont(10));
    m_themeCombo->setCursor(Qt::PointingHandCursor);
    connect(m_themeCombo, &QComboBox::currentTextChanged, this, &OnboardingWizard::previewTheme);
    p3Layout->addWidget(m_themeCombo);
    p3Layout->addStretch();

    // ─────────────────────────────────────────────────────────────────────────
    // Page 4: Success
    // ─────────────────────────────────────────────────────────────────────────
    QWidget* page4 = new QWidget();
    QVBoxLayout* p4Layout = new QVBoxLayout(page4);
    p4Layout->setContentsMargins(30, 30, 30, 30);
    p4Layout->setSpacing(15);

    QLabel* p4Logo = new QLabel();
    if (QFile::exists(iconPath)) {
        p4Logo->setPixmap(QIcon(iconPath).pixmap(80, 80));
    }
    p4Logo->setAlignment(Qt::AlignCenter);
    p4Layout->addWidget(p4Logo);

    QLabel* p4Title = new QLabel("You're All Set! 🎉");
    p4Title->setFont(ThemeManager::instance().qtFont(14, true));
    p4Title->setStyleSheet(QString("color: %1; background: transparent; border: none;").arg(p.accent2));
    p4Title->setAlignment(Qt::AlignCenter);
    p4Layout->addWidget(p4Title);

    QLabel* p4Desc = new QLabel(
        "Awesome job! Setup is completely finished.\n\n"
        "When you proceed, the ToolBox dashboard will open. "
        "Simply click 'Download' or 'Run' on any script to instantly deploy "
        "and manage it in a separate, isolated virtual environment.\n\n"
        "Enjoy your experience, and remember we're here on Discord if you ever need help! :3"
    );
    p4Desc->setFont(ThemeManager::instance().qtFont(10));
    p4Desc->setWordWrap(true);
    p4Desc->setAlignment(Qt::AlignCenter);
    p4Desc->setStyleSheet("background: transparent; border: none;");
    p4Layout->addWidget(p4Desc);
    p4Layout->addStretch();

    // Add to stack
    m_stack->addWidget(page1);
    m_stack->addWidget(page2);
    m_stack->addWidget(page3);
    m_stack->addWidget(page4);

    // Main layout setup
    QVBoxLayout* rootLayout = new QVBoxLayout(this);
    rootLayout->setContentsMargins(0, 0, 0, 0);
    rootLayout->setSpacing(0);

    QFrame* bodyPanel = new QFrame();
    bodyPanel->setStyleSheet(QString("background-color: %1; border: none;").arg(p.panel));
    QVBoxLayout* bodyPanelLayout = new QVBoxLayout(bodyPanel);
    bodyPanelLayout->setContentsMargins(0, 0, 0, 0);
    bodyPanelLayout->addWidget(m_stack);
    rootLayout->addWidget(bodyPanel, 1);

    QFrame* divider = new QFrame();
    divider->setFixedHeight(1);
    divider->setStyleSheet(QString("background-color: %1; border: none;").arg(p.border));
    rootLayout->addWidget(divider);

    QWidget* navPanel = new QWidget();
    navPanel->setStyleSheet(QString("background-color: %1;").arg(p.bg));
    QHBoxLayout* navLayout = new QHBoxLayout(navPanel);
    navLayout->setContentsMargins(20, 10, 20, 15);

    m_backBtn = new QPushButton("← Back");
    m_backBtn->setStyleSheet(ThemeManager::instance().subtleButtonQss());
    m_backBtn->setFont(ThemeManager::instance().qtFont(9, true));
    m_backBtn->setCursor(Qt::PointingHandCursor);
    m_backBtn->setMinimumWidth(90);
    connect(m_backBtn, &QPushButton::clicked, this, &OnboardingWizard::goBack);
    navLayout->addWidget(m_backBtn);

    navLayout->addStretch(1);

    m_nextBtn = new QPushButton("Next →");
    m_nextBtn->setStyleSheet(ThemeManager::instance().accentButtonQss());
    m_nextBtn->setFont(ThemeManager::instance().qtFont(9, true));
    m_nextBtn->setCursor(Qt::PointingHandCursor);
    m_nextBtn->setMinimumWidth(100);
    connect(m_nextBtn, &QPushButton::clicked, this, &OnboardingWizard::goNext);
    navLayout->addWidget(m_nextBtn);

    rootLayout->addWidget(navPanel);

    updateNavButtons();
}

void OnboardingWizard::browseFolder() {
    QString chosen = QFileDialog::getExistingDirectory(this, "Choose Tools Folder", m_toolsDir);
    if (!chosen.isEmpty()) {
        m_toolsDir = QDir::toNativeSeparators(chosen);
        m_pathEntry->setText(m_toolsDir);
    }
}

void OnboardingWizard::useDefaultPath() {
    m_toolsDir = QDir(QStandardPaths::writableLocation(QStandardPaths::GenericDataLocation)).filePath("CToolBox-Launcher");
    m_toolsDir = QDir::toNativeSeparators(m_toolsDir);
    m_pathEntry->setText(m_toolsDir);
}

void OnboardingWizard::previewTheme(const QString& labelText) {
    QMap<QString, QString> labels = ThemeManager::instance().labels();
    for (auto it = labels.begin(); it != labels.end(); ++it) {
        if (it.value() == labelText) {
            m_selectedTheme = it.key();
            ThemeManager::instance().setTheme(m_selectedTheme);
            ThemePalette p = ThemeManager::instance().currentPalette();
            setStyleSheet(QString("background-color: %1; color: %2;").arg(p.bg, p.text));
            m_pathEntry->setStyleSheet(ThemeManager::instance().lineEditQss());
            break;
        }
    }
}

void OnboardingWizard::updateNavButtons() {
    int idx = m_stack->currentIndex();
    m_backBtn->setEnabled(idx > 0);
    if (idx == m_stack->count() - 1) {
        m_nextBtn->setText("Get Started! 🎉");
    } else {
        m_nextBtn->setText("Next →");
    }
}

void OnboardingWizard::goBack() {
    int idx = m_stack->currentIndex();
    if (idx > 0) {
        m_stack->setCurrentIndex(idx - 1);
        updateNavButtons();
    }
}

void OnboardingWizard::goNext() {
    int idx = m_stack->currentIndex();
    if (idx < m_stack->count() - 1) {
        m_stack->setCurrentIndex(idx + 1);
        updateNavButtons();
    } else {
        accept();
    }
}
