#pragma once
#include <QMainWindow>
#include <QVBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QScrollArea>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QMap>
#include <memory>
#include "configmanager.h"

enum class ToolState {
    Missing,
    Update,
    Current
};

class MainWindow : public QMainWindow {
    Q_OBJECT
public:
    MainWindow();
    ~MainWindow() override;
private slots:
    void refreshMainButtons();
    void refreshButtonLabels();
    void applyTheme(const QString& mode);
    void openHelp();
    void openSettings();
    void openConsole();
    void launchTool(const QString& filename);
    
    void checkForUpdates();
    void fetchRepoTree();
    void scanToolsVersions();
    void syncTool(const QString& filename, ToolState state);
    void launchLHM();
    
private:
    void buildRoot();
    ToolState getToolState(const QString& filename) const;
    QString toolButtonLabel(const ManagedScript& s) const;
    void patchLHMConfig();
    bool ensureLHM();
    void runDetached(const QString& filename);
    void startAutoUpdate(const QString& remoteVer);

    struct SyncContext {
        int currentFileIndex = 0;
        QStringList files;
        QString filename;
    };

    struct ScanContext {
        int currentIdx = 0;
        QVector<ManagedScript> scripts;
    };

    void downloadNextFile(std::shared_ptr<SyncContext> context);
    void scanNextTool(std::shared_ptr<ScanContext> context);
    
    QNetworkAccessManager* m_networkManager;
    QScrollArea* m_buttonsScroll;
    QVBoxLayout* m_buttonsLayout;
    QLabel* m_footerLabel;
    
    QMap<QString, ToolState> m_toolStates;
    QMap<QString, QString> m_remoteVersions;
    QVector<QPushButton*> m_scriptButtons;
    
    QStringList m_gitTreePaths;
    bool m_treeFetched;
};
