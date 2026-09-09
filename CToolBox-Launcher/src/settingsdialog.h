#pragma once
#include <QDialog>
#include <QLineEdit>
#include <QComboBox>
#include <QScrollArea>
#include <QVBoxLayout>
#include <QLabel>
#include <QJsonArray>

class SettingsDialog : public QDialog {
    Q_OBJECT
signals:
    void themeChanged(const QString& mode);
    void scriptsChanged();
public:
    explicit SettingsDialog(QWidget* parent = nullptr);
protected:
    bool eventFilter(QObject* watched, QEvent* event) override;
private slots:
    void changeBranch(const QString& newBranch);
    void browsePython();
    void resetPython();
    void changeToolsFolder();
    void toggleThemes();
    void selectTheme(const QString& mode);
    void refreshScriptList();
    void removeScript(int idx);
    void addScript();
private:
    QLineEdit* m_pythonEntry;
    QLineEdit* m_toolsEntry;
    QComboBox* m_branchCombo;
    
    QLabel* m_themeArrow;
    QLabel* m_themePreview;
    QLabel* m_themeRestartLbl;
    QWidget* m_themeBody;
    bool m_themesOpen;
    
    QVBoxLayout* m_scriptListLayout;
};
