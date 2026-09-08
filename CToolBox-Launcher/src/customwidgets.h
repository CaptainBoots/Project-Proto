#pragma once
#include <QWidget>
#include <QLabel>
#include <QDialog>
#include <QTextEdit>
#include <QPushButton>

class StripeBackground : public QWidget {
    Q_OBJECT
public:
    explicit StripeBackground(QWidget* parent = nullptr);
protected:
    void paintEvent(QPaintEvent* event) override;
};

class TextChip : public QLabel {
    Q_OBJECT
public:
    explicit TextChip(const QString& text = "", const QString& fg = "", const QString& bg = "", int radius = 3, const QString& padding = "3px 10px", QWidget* parent = nullptr);
protected:
    void paintEvent(QPaintEvent* event) override;
private:
    QColor m_chipBg;
    int m_radius;
};

class CircleToggle : public QWidget {
    Q_OBJECT
signals:
    void toggled(bool value);
public:
    explicit CircleToggle(QWidget* parent = nullptr, bool enabled = true, const QString& colour = "", int size = 20, int pad = 3);
    void set(bool value);
    bool get() const { return m_enabled; }
protected:
    void paintEvent(QPaintEvent* event) override;
    void mousePressEvent(QMouseEvent* event) override;
private:
    bool m_enabled;
    QColor m_color;
    int m_size;
    int m_pad;
};

class ConsoleWindow : public QDialog {
    Q_OBJECT
public:
    explicit ConsoleWindow(QWidget* parent = nullptr);
    static void appendLog(const QString& text);
    static QString getLogs();
    static void clearLogs();
public slots:
    void updateLogs();
private:
    QTextEdit* m_textArea;
    static QString s_logBuffer;
    static ConsoleWindow* s_instance;
};
