#include "helpdialog.h"
#include "theme.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QFrame>

HelpDialog::HelpDialog(QWidget* parent) : QDialog(parent), m_currentPage(0) {
    setWindowTitle("Documentation & Guide");
    setFixedSize(520, 460);
    ThemePalette p = ThemeManager::instance().currentPalette();
    setStyleSheet(QString("background-color: %1;").arg(p.bg));

    m_pages = {
        {
            "Welcome to ToolBox",
            "This control centre manages and runs various modular optimization tools "
            "tailored for companion OSC network tracking.\n\n"
            "Features include:\n"
            "• Automated system update patches on initialization cycles.\n"
            "• Sandbox virtual execution container environments.\n"
            "• Fast preference configuration overlays."
        },
        {
            "Status Indicator",
            "The status shelf located across the footer displays active telemetry feedback:\n"
            "• 'Ready' — waiting for action\n"
            "• 'Starting up (ScriptName)' — launching\n"
            "• 'Up to date' — version check complete\n"
            "• 'Error' — something went wrong"
        },
        {
            "Available Scripts",
            "▶ Router — Manages OSC routing\n"
            " Forwards OSC messages between sources\n"
            " and destinations.\n\n"
            "▶ ChatBox — Sends data over OSC\n"
            " Displays system info, weather, music,\n"
            " and custom messages.\n\n"
            "▶ Face Tracking Controller — Control\n"
            " face tracking features."
        },
        {
            "Status Bar",
            "The top bar of each script shows:\n\n"
            "Left: Script name and icon\n"
            "Centre: Version number\n"
            "Right: Current status\n\n"
            "Status Examples:\n"
            "• Status: Running — Script is active\n"
            "• Status: Stopped — Script is inactive\n"
            "• Status: Error — Something failed"
        },
        {
            "Adding a Script",
            "1. Click the ⚙ (gear) button in the footer\n"
            "2. Click '+ Add Script' button\n"
            "3. Enter a label (button text)\n"
            "4. Enter filename or full path\n"
            "5. Click 'Add' to save\n\n"
            "Your new script button appears in\n"
            "'MANAGED SCRIPTS' section immediately!"
        },
        {
            "Removing a Script",
            "1. Click the ⚙ (gear) button\n"
            "2. Find the script in the list\n"
            "3. Click the '✕ Remove' button\n"
            "4. Script removed from buttons\n\n"
            "Changes save automatically. Close and\n"
            "reopen ToolBox to fully refresh if needed."
        },
        {
            "Tips",
            "• Always start Router first, then ChatBox\n\n"
            "• Each script remembers its settings\n"
            " between sessions\n\n"
            "• Check your internet connection if\n"
            " scripts fail to start\n\n"
            "• Run scripts from the ToolBox for\n"
            " proper management"
        }
    };

    QVBoxLayout* rootLayout = new QVBoxLayout(this);
    rootLayout->setContentsMargins(0, 0, 0, 0);
    rootLayout->setSpacing(0);

    // Header
    QWidget* hdr = new QWidget();
    hdr->setStyleSheet(QString("background-color: %1;").arg(p.panel));
    QHBoxLayout* hdrLayout = new QHBoxLayout(hdr);
    hdrLayout->setContentsMargins(20, 10, 20, 10);
    m_titleLabel = new QLabel("");
    m_titleLabel->setStyleSheet(QString("color: %1; background: transparent; border: none;").arg(p.accent2));
    m_titleLabel->setFont(ThemeManager::instance().qtFont(12, true));
    hdrLayout->addWidget(m_titleLabel);
    rootLayout->addWidget(hdr);

    QFrame* divider = new QFrame();
    divider->setFixedHeight(1);
    divider->setStyleSheet(QString("background-color: %1; border: none;").arg(p.border));
    rootLayout->addWidget(divider);

    // Body
    QWidget* bodyWrap = new QWidget();
    QVBoxLayout* bodyWrapLayout = new QVBoxLayout(bodyWrap);
    bodyWrapLayout->setContentsMargins(20, 16, 20, 0);

    QFrame* contentPanel = new QFrame();
    contentPanel->setStyleSheet(QString("background-color: %1; border: none;").arg(p.panel));
    QVBoxLayout* contentLayout = new QVBoxLayout(contentPanel);
    contentLayout->setContentsMargins(14, 14, 14, 14);

    m_contentLabel = new QLabel("");
    m_contentLabel->setStyleSheet(QString("color: %1; background: transparent; border: none;").arg(p.text));
    m_contentLabel->setFont(ThemeManager::instance().qtFont(10));
    m_contentLabel->setWordWrap(true);
    m_contentLabel->setAlignment(Qt::AlignLeft | Qt::AlignTop);
    contentLayout->addWidget(m_contentLabel);

    bodyWrapLayout->addWidget(contentPanel);
    rootLayout->addWidget(bodyWrap, 1);

    // Footer Nav
    QHBoxLayout* navFrame = new QHBoxLayout();
    navFrame->setContentsMargins(20, 8, 20, 14);

    m_prevBtn = new QPushButton("← Back");
    m_prevBtn->setStyleSheet(ThemeManager::instance().subtleButtonQss());
    m_prevBtn->setFont(ThemeManager::instance().qtFont(9, true));
    m_prevBtn->setFixedWidth(100);
    connect(m_prevBtn, &QPushButton::clicked, this, &HelpDialog::goBack);
    navFrame->addWidget(m_prevBtn);
    navFrame->addStretch(1);

    m_pageIndicator = new QLabel("");
    m_pageIndicator->setStyleSheet(QString("color: %1; background: transparent; border: none;").arg(p.subtext));
    m_pageIndicator->setFont(ThemeManager::instance().qtFont(9));
    navFrame->addWidget(m_pageIndicator);
    navFrame->addStretch(1);

    m_nextBtn = new QPushButton("Next →");
    m_nextBtn->setStyleSheet(ThemeManager::instance().accentButtonQss());
    m_nextBtn->setFont(ThemeManager::instance().qtFont(9, true));
    m_nextBtn->setFixedWidth(100);
    connect(m_nextBtn, &QPushButton::clicked, this, &HelpDialog::nextOrFinish);
    navFrame->addWidget(m_nextBtn);

    rootLayout->addLayout(navFrame);

    showPage(0);
}

void HelpDialog::showPage(int idx) {
    if (idx < 0 || idx >= m_pages.size()) return;
    m_currentPage = idx;
    HelpPage p = m_pages[idx];
    m_titleLabel->setText(p.title);
    m_contentLabel->setText(p.content);
    m_pageIndicator->setText(QString("Page %1 of %2").arg(idx + 1).arg(m_pages.size()));
    m_prevBtn->setEnabled(idx > 0);
    bool isLast = idx == m_pages.size() - 1;
    m_nextBtn->setText(isLast ? "Finish" : "Next →");
}

void HelpDialog::goBack() {
    if (m_currentPage > 0) {
        showPage(m_currentPage - 1);
    }
}

void HelpDialog::nextOrFinish() {
    if (m_currentPage < m_pages.size() - 1) {
        showPage(m_currentPage + 1);
    } else {
        close();
    }
}
