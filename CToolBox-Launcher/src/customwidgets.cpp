#include "customwidgets.h"
#include "theme.h"
#include <QPainter>
#include <QMouseEvent>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QApplication>
#include <QClipboard>

// StripeBackground
StripeBackground::StripeBackground(QWidget* parent) : QWidget(parent) {
    setAutoFillBackground(false);
}

void StripeBackground::paintEvent(QPaintEvent* /*event*/) {
    QPainter painter(this);
    painter.setRenderHint(QPainter::Antialiasing, false);
    int w = width();
    int h = height();
    ThemePalette p = ThemeManager::instance().currentPalette();
    if (p.stripe_colours.isEmpty()) {
        painter.fillRect(rect(), QColor(p.bg));
        return;
    }

    painter.fillRect(rect(), QColor(p.bg));
    int stripe_w = 28;
    int cycle = stripe_w * p.stripe_colours.size();
    int extent = w + h + cycle * 2;
    int start = -cycle;
    while (start < extent) {
        for (int i = 0; i < p.stripe_colours.size(); ++i) {
            int x0 = start + i * stripe_w;
            QPolygonF poly;
            poly << QPointF(x0, 0)
                 << QPointF(x0 + stripe_w, 0)
                 << QPointF(x0 + stripe_w + h, h)
                 << QPointF(x0 + h, h);
            painter.setBrush(QColor(p.stripe_colours[i]));
            painter.setPen(Qt::NoPen);
            painter.drawPolygon(poly);
        }
        start += cycle;
    }
}

// TextChip
TextChip::TextChip(const QString& text, const QString& fg, const QString& bg, int radius, const QString& padding, QWidget* parent)
    : QLabel(text, parent), m_radius(radius) {
    ThemePalette p = ThemeManager::instance().currentPalette();
    m_chipBg = QColor(bg.isEmpty() ? p.panel : bg);
    QString fgColor = fg.isEmpty() ? p.accent2 : fg;
    setStyleSheet(QString("color: %1; background: transparent; padding: %2; border: none;").arg(fgColor, padding));
}

void TextChip::paintEvent(QPaintEvent* event) {
    QPainter painter(this);
    painter.setRenderHint(QPainter::Antialiasing, true);
    painter.setBrush(m_chipBg);
    painter.setPen(Qt::NoPen);
    painter.drawRoundedRect(rect(), m_radius, m_radius);
    painter.end();
    QLabel::paintEvent(event);
}

// CircleToggle
CircleToggle::CircleToggle(QWidget* parent, bool enabled, const QString& colour, int size, int pad)
    : QWidget(parent), m_enabled(enabled), m_size(size), m_pad(pad) {
    ThemePalette p = ThemeManager::instance().currentPalette();
    m_color = QColor(colour.isEmpty() ? p.accent : colour);
    setFixedSize(size, size);
    setCursor(Qt::PointingHandCursor);
}

void CircleToggle::paintEvent(QPaintEvent* /*event*/) {
    QPainter painter(this);
    painter.setRenderHint(QPainter::Antialiasing, true);
    QRectF rect(m_pad, m_pad, m_size - 2 * m_pad, m_size - 2 * m_pad);
    if (m_enabled) {
        painter.setBrush(m_color);
        painter.setPen(Qt::NoPen);
    } else {
        painter.setBrush(Qt::NoBrush);
        painter.setPen(QPen(m_color, 2));
    }
    painter.drawEllipse(rect);
}

void CircleToggle::mousePressEvent(QMouseEvent* event) {
    if (event->button() == Qt::LeftButton) {
        m_enabled = !m_enabled;
        update();
        emit toggled(m_enabled);
    }
}

void CircleToggle::set(bool value) {
    m_enabled = value;
    update();
}

// ConsoleWindow
QString ConsoleWindow::s_logBuffer = "";
ConsoleWindow* ConsoleWindow::s_instance = nullptr;

ConsoleWindow::ConsoleWindow(QWidget* parent) : QDialog(parent) {
    s_instance = this;
    setWindowTitle("CToolBox-Launcher Console Log");
    resize(700, 450);
    ThemePalette p = ThemeManager::instance().currentPalette();
    setStyleSheet(QString("background-color: %1; color: %2;").arg(p.bg, p.text));

    QVBoxLayout* layout = new QVBoxLayout(this);
    layout->setContentsMargins(10, 10, 10, 10);
    layout->setSpacing(10);

    QLabel* titleLabel = new QLabel("Real-Time Application Console Logs");
    QFont titleFont = ThemeManager::instance().qtFont(11, true);
    titleLabel->setFont(titleFont);
    titleLabel->setStyleSheet(QString("color: %1; background: transparent; border: none;").arg(p.accent));
    layout->addWidget(titleLabel);

    m_textArea = new QTextEdit();
    m_textArea->setReadOnly(true);
    m_textArea->setFont(QFont("Consolas", 9));
    m_textArea->setStyleSheet(
        QString("background-color: %1; color: %2; border: 1px solid %3; border-radius: 4px; padding: 5px;")
        .arg(p.panel, p.text, p.border)
    );
    layout->addWidget(m_textArea);

    QHBoxLayout* btnLayout = new QHBoxLayout();
    btnLayout->setSpacing(10);

    QPushButton* clearBtn = new QPushButton("Clear");
    clearBtn->setCursor(Qt::PointingHandCursor);
    clearBtn->setStyleSheet(
        QString("QPushButton { background-color: %1; color: %2; border: 1px solid %3; border-radius: 3px; padding: 5px 15px; }"
                "QPushButton:hover { background-color: %3; color: %4; }")
        .arg(p.panel, p.subtext, p.border, p.text)
    );
    connect(clearBtn, &QPushButton::clicked, this, &ConsoleWindow::clearLogs);
    btnLayout->addWidget(clearBtn);

    QPushButton* copyBtn = new QPushButton("Copy to Clipboard");
    copyBtn->setCursor(Qt::PointingHandCursor);
    copyBtn->setStyleSheet(
        QString("QPushButton { background-color: %1; color: %2; border: 1px solid %3; border-radius: 3px; padding: 5px 15px; }"
                "QPushButton:hover { background-color: %3; color: %4; }")
        .arg(p.panel, p.subtext, p.border, p.text)
    );
    connect(copyBtn, &QPushButton::clicked, this, [this]() {
        QApplication::clipboard()->setText(m_textArea->toPlainText());
    });
    btnLayout->addWidget(copyBtn);

    btnLayout->addStretch();

    QPushButton* closeBtn = new QPushButton("Close");
    closeBtn->setCursor(Qt::PointingHandCursor);
    closeBtn->setStyleSheet(ThemeManager::instance().accentButtonQss());
    connect(closeBtn, &QPushButton::clicked, this, &ConsoleWindow::close);
    btnLayout->addWidget(closeBtn);

    layout->addLayout(btnLayout);

    m_textArea->setPlainText(s_logBuffer);
    m_textArea->moveCursor(QTextCursor::End);
}

void ConsoleWindow::appendLog(const QString& text) {
    s_logBuffer.append(text);
    if (s_logBuffer.length() > 500000) {
        s_logBuffer = s_logBuffer.right(300000);
    }
    if (s_instance) {
        s_instance->updateLogs();
    }
}

QString ConsoleWindow::getLogs() {
    return s_logBuffer;
}

void ConsoleWindow::clearLogs() {
    s_logBuffer.clear();
    if (s_instance) {
        s_instance->updateLogs();
    }
}

void ConsoleWindow::updateLogs() {
    if (m_textArea) {
        m_textArea->setPlainText(s_logBuffer);
        m_textArea->moveCursor(QTextCursor::End);
    }
}
