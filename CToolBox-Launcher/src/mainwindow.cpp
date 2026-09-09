#include "mainwindow.h"
#include "theme.h"
#include "settingsdialog.h"
#include "helpdialog.h"
#include "customwidgets.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QFrame>
#include <QMessageBox>
#include <QProcess>
#include <QDir>
#include <QFile>
#include <QTextStream>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QRegularExpression>
#include <QTimer>
#include <QCoreApplication>
#include <QDesktopServices>
#include <QUrl>
#include <QSet>
#include <QProgressDialog>

#ifdef Q_OS_WIN
#include <windows.h>
#include <shellapi.h>
#endif

MainWindow::MainWindow() : m_treeFetched(false) {
    m_networkManager = new QNetworkAccessManager(this);
    
    ConfigManager::instance().load();
    ThemeManager::instance().setTheme(ThemeManager::instance().currentMode());

    buildRoot();
    refreshMainButtons();

    // Automatically check for updates and scan versions
    QTimer::singleShot(500, this, &MainWindow::checkForUpdates);
}

MainWindow::~MainWindow() = default;

void MainWindow::buildRoot() {
    setWindowTitle("CToolBox-Launcher");
    resize(580, 600);
    setMinimumSize(480, 380);

    ThemePalette p = ThemeManager::instance().currentPalette();
    setStyleSheet(ThemeManager::instance().qss());

    StripeBackground* central = new StripeBackground(this);
    QVBoxLayout* rootLayout = new QVBoxLayout(central);
    rootLayout->setContentsMargins(0, 0, 0, 0);
    rootLayout->setSpacing(0);

    // ── Header ────────────────────────────────────────────────────────
    QWidget* header = new QWidget();
    header->setStyleSheet(QString("background-color: %1;").arg(p.panel));
    QHBoxLayout* headerLayout = new QHBoxLayout(header);
    headerLayout->setContentsMargins(20, 12, 20, 12);

    QLabel* titleLbl = new QLabel("◈ CToolBox-Launcher");
    titleLbl->setStyleSheet(QString("color: %1; background: transparent; border: none;").arg(p.accent2));
    titleLbl->setFont(ThemeManager::instance().qtFont(16, true));
    headerLayout->addWidget(titleLbl);
    headerLayout->addStretch(1);

    QLabel* versionLbl = new QLabel(QString("v%1").arg(ConfigManager::instance().version()));
    versionLbl->setStyleSheet(QString("color: %1; background: transparent; border: none;").arg(p.subtext));
    versionLbl->setFont(ThemeManager::instance().qtFont(9));
    headerLayout->addWidget(versionLbl);

    rootLayout->addWidget(header);

    QFrame* divider = new QFrame();
    divider->setFixedHeight(1);
    divider->setStyleSheet(QString("background-color: %1; border: none;").arg(p.border));
    rootLayout->addWidget(divider);

    // ── Main Content ──────────────────────────────────────────────────
    QWidget* mainArea = new QWidget();
    mainArea->setStyleSheet("background: transparent;");
    QVBoxLayout* mainLayout = new QVBoxLayout(mainArea);
    mainLayout->setContentsMargins(24, 16, 24, 16);
    mainLayout->setSpacing(0);

    TextChip* toolsLabel = new TextChip("MANAGED SCRIPTS", p.accent, "", 3, "3px 8px", mainArea);
    toolsLabel->setFont(ThemeManager::instance().qtFont(9, true));
    mainLayout->addWidget(toolsLabel);
    mainLayout->addSpacing(10);

    m_buttonsScroll = new QScrollArea();
    m_buttonsScroll->setWidgetResizable(true);
    m_buttonsScroll->setStyleSheet("background: transparent; border: none;");

    QWidget* buttonsInner = new QWidget();
    buttonsInner->setStyleSheet("background: transparent;");
    m_buttonsLayout = new QVBoxLayout(buttonsInner);
    m_buttonsLayout->setContentsMargins(0, 0, 4, 0);
    m_buttonsLayout->setSpacing(4);
    m_buttonsLayout->addStretch(1);

    m_buttonsScroll->setWidget(buttonsInner);
    mainLayout->addWidget(m_buttonsScroll, 1);

    rootLayout->addWidget(mainArea, 1);

    // ── Footer ────────────────────────────────────────────────────────
    QWidget* footerBar = new QWidget();
    footerBar->setStyleSheet(QString("background-color: %1;").arg(p.panel));
    QVBoxLayout* footerOuter = new QVBoxLayout(footerBar);
    footerOuter->setContentsMargins(0, 6, 0, 4);
    footerOuter->setSpacing(2);

    QHBoxLayout* footerRow = new QHBoxLayout();
    footerRow->setContentsMargins(8, 0, 8, 0);

    QPushButton* helpBtn = new QPushButton("?");
    helpBtn->setFixedSize(28, 28);
    helpBtn->setStyleSheet(ThemeManager::instance().subtleButtonQss() + "QPushButton { padding: 0; font-size: 12px; }");
    helpBtn->setCursor(Qt::PointingHandCursor);
    connect(helpBtn, &QPushButton::clicked, this, &MainWindow::openHelp);
    footerRow->addWidget(helpBtn);
    
    footerRow->addStretch(1);

    QPushButton* consoleBtn = new QPushButton("⌨");
    consoleBtn->setFixedSize(28, 28);
    consoleBtn->setStyleSheet(ThemeManager::instance().subtleButtonQss() + "QPushButton { padding: 0; font-size: 12px; }");
    consoleBtn->setCursor(Qt::PointingHandCursor);
    connect(consoleBtn, &QPushButton::clicked, this, &MainWindow::openConsole);
    footerRow->addWidget(consoleBtn);

    QPushButton* settingsBtn = new QPushButton("⚙");
    settingsBtn->setFixedSize(28, 28);
    settingsBtn->setStyleSheet(ThemeManager::instance().subtleButtonQss() + "QPushButton { padding: 0; font-size: 12px; }");
    settingsBtn->setCursor(Qt::PointingHandCursor);
    connect(settingsBtn, &QPushButton::clicked, this, &MainWindow::openSettings);
    footerRow->addWidget(settingsBtn);

    footerOuter->addLayout(footerRow);

    m_footerLabel = new QLabel("Checking for updates on startup...");
    m_footerLabel->setAlignment(Qt::AlignCenter);
    m_footerLabel->setStyleSheet(QString("color: %1; background: transparent; border: none;").arg(p.subtext));
    m_footerLabel->setFont(ThemeManager::instance().qtFont(8));
    footerOuter->addWidget(m_footerLabel);

    rootLayout->addWidget(footerBar);

    setCentralWidget(central);
}

void MainWindow::refreshMainButtons() {
    // Clear old buttons
    QLayoutItem* item;
    while ((item = m_buttonsLayout->takeAt(0)) != nullptr) {
        delete item->widget();
        delete item;
    }

    m_scriptButtons.clear();
    QVector<ManagedScript> scripts = ConfigManager::instance().managedScripts();
    ThemePalette p = ThemeManager::instance().currentPalette();

    for (int i = 0; i < scripts.size(); ++i) {
        ManagedScript script = scripts[i];
        
        QPushButton* btn = new QPushButton(toolButtonLabel(script));
        btn->setStyleSheet(
            QString("QPushButton { background-color: %1; color: %2; border: 1px solid %3; "
                    "border-radius: 3px; padding: 8px 20px; font-weight: bold; text-align: left; }"
                    "QPushButton:hover { background-color: %4; color: %5; }")
            .arg(p.panel, p.text, p.border, p.accent, p.text2)
        );
        btn->setFont(ThemeManager::instance().qtFont(10, true));
        btn->setCursor(Qt::PointingHandCursor);
        
        QString filename = script.filename;
        connect(btn, &QPushButton::clicked, this, [this, filename]() { launchTool(filename); });
        
        m_buttonsLayout->insertWidget(i, btn);
        m_scriptButtons.append(btn);
    }

    m_buttonsLayout->addStretch(1);

    int btnCount = scripts.size();
    resize(580, qMin(440 + btnCount * 52, 820));
}

void MainWindow::refreshButtonLabels() {
    QVector<ManagedScript> scripts = ConfigManager::instance().managedScripts();
    for (int i = 0; i < scripts.size() && i < m_scriptButtons.size(); ++i) {
        m_scriptButtons[i]->setText(toolButtonLabel(scripts[i]));
    }
}

void MainWindow::applyTheme(const QString& mode) {
    ThemeManager::instance().setTheme(mode);
    buildRoot();
    refreshMainButtons();
}

void MainWindow::openHelp() {
    HelpDialog dlg(this);
    dlg.exec();
}

void MainWindow::openSettings() {
    SettingsDialog dlg(this);
    connect(&dlg, &SettingsDialog::themeChanged, this, &MainWindow::applyTheme);
    connect(&dlg, &SettingsDialog::scriptsChanged, this, [this]() {
        refreshMainButtons();
        fetchRepoTree();
    });
    dlg.exec();
}

ToolState MainWindow::getToolState(const QString& filename) const {
    if (m_toolStates.contains(filename)) {
        return m_toolStates[filename];
    }
    
    // Check if file exists locally
    QString localPath = QDir(ConfigManager::instance().toolsRootDir()).filePath(filename);
    if (QFile::exists(localPath)) {
        return ToolState::Current;
    }
    return ToolState::Missing;
}

QString MainWindow::toolButtonLabel(const ManagedScript& s) const {
    ToolState state = getToolState(s.filename);
    if (state == ToolState::Missing) {
        return "Download " + s.label;
    } else if (state == ToolState::Update) {
        return "Update " + s.label;
    }
    return "Run " + s.label;
}

void MainWindow::launchTool(const QString& filename) {
    if (filename == "LibreHardwareMonitor/LibreHardwareMonitor.exe") {
        launchLHM();
        return;
    }

    ToolState state = getToolState(filename);
    if (state == ToolState::Missing) {
        m_footerLabel->setText("Downloading " + filename + "... (please wait)");
        syncTool(filename, ToolState::Missing);
    } else if (state == ToolState::Update) {
        m_footerLabel->setText("Updating " + filename + "... (please wait)");
        syncTool(filename, ToolState::Update);
    } else {
        m_footerLabel->setText("Starting up " + filename + "...");
        runDetached(filename);
    }
}

void MainWindow::runDetached(const QString& filename) {
    QString fullPath = QDir(ConfigManager::instance().toolsRootDir()).filePath(filename);
    QString scriptDir = QFileInfo(fullPath).absolutePath();
    
    QString python = ConfigManager::instance().activePython();
    QString scriptFile = QFileInfo(fullPath).fileName();

    qDebug() << "Launching script:" << python << scriptFile << "in" << scriptDir;
    
    bool ok = QProcess::startDetached(python, {scriptFile}, scriptDir);
    if (ok) {
        m_footerLabel->setText("Ready");
        ConsoleWindow::appendLog("[Launcher] Successfully started detached process: " + filename + "\n");
    } else {
        m_footerLabel->setText("Error launching script");
        QMessageBox::critical(this, "Launch Error", "Failed to start " + filename + ".\n\nVerify that Python is installed and configured correctly.");
    }
}

void MainWindow::syncTool(const QString& filename, ToolState targetState) {
    if (!m_treeFetched) {
        fetchRepoTree();
        // Retry syncing in a short moment once tree is loaded
        QTimer::singleShot(1000, this, [this, filename, targetState]() {
            syncTool(filename, targetState);
        });
        return;
    }

    QString folderName = filename.split("/")[0];
    QString prefix = folderName + "/";

    QStringList filesToSync;
    for (const QString& path : m_gitTreePaths) {
        if (path.startsWith(prefix, Qt::CaseInsensitive)) {
            filesToSync.append(path);
        }
    }

    if (filesToSync.isEmpty()) {
        m_footerLabel->setText("Error: no files discovered in repo tree for " + filename);
        return;
    }

    setEnabled(false);
    
    // Download files sequentially using recursion
    struct SyncContext {
        int currentFileIndex = 0;
        QStringList files;
        MainWindow* self;
        QString filename;
    };

    auto context = std::make_shared<SyncContext>();
    context->files = filesToSync;
    context->self = this;
    context->filename = filename;

    // Recursive lambda for downloading files
    auto downloadNext = std::make_shared<std::function<void()>>();
    *downloadNext = [context, downloadNext]() {
        if (context->currentFileIndex >= context->files.size()) {
            // Done downloading all files for this tool!
            // Read main.py to extract and cache the real tool NAME
            QString localMainPy = QDir(ConfigManager::instance().toolsRootDir()).filePath(context->filename);
            QFile file(localMainPy);
            if (file.open(QIODevice::ReadOnly | QIODevice::Text)) {
                QTextStream in(&file);
                QString content = in.readAll();
                file.close();

                QRegularExpression re("NAME\\s*=\\s*['\"]([^'\"]+)['\"]");
                QRegularExpressionMatch match = re.match(content);
                if (match.hasMatch()) {
                    QString realName = match.captured(1);
                    
                    // Update label in managed scripts
                    QVector<ManagedScript> scripts = ConfigManager::instance().managedScripts();
                    for (int i = 0; i < scripts.size(); ++i) {
                        if (scripts[i].filename == context->filename) {
                            scripts[i].label = realName;
                            break;
                        }
                    }
                    ConfigManager::instance().setManagedScripts(scripts);
                    
                    // Cache the label
                    ConfigManager::instance().setCachedLabel(context->filename, realName);
                    ConfigManager::instance().save();
                    
                    context->self->refreshMainButtons();
                }
            }

            context->self->setEnabled(true);
            context->self->m_toolStates[context->filename] = ToolState::Current;
            context->self->m_footerLabel->setText("Ready");
            context->self->refreshButtonLabels();
            context->self->runDetached(context->filename);
            return;
        }

        QString relPath = context->files[context->currentFileIndex];
        QString localDest = QDir(ConfigManager::instance().toolsRootDir()).filePath(relPath);
        QDir().mkpath(QFileInfo(localDest).absolutePath());

        QString url = QString("https://raw.githubusercontent.com/CaptainBoots/Nova-Tools/%1/%2")
                      .arg(ConfigManager::instance().updateBranch(), relPath);

        QNetworkReply* reply = context->self->m_networkManager->get(QNetworkRequest(QUrl(url)));
        connect(reply, &QNetworkReply::finished, context->self, [context, reply, localDest, relPath, downloadNext]() {
            if (reply->error() == QNetworkReply::NoError) {
                QFile file(localDest);
                if (file.open(QIODevice::WriteOnly)) {
                    file.write(reply->readAll());
                    file.close();
                    ConsoleWindow::appendLog("[Sync] Downloaded: " + relPath + "\n");
                }
            } else {
                ConsoleWindow::appendLog("[Sync Error] Failed to download: " + relPath + "\n");
            }
            reply->deleteLater();
            context->currentFileIndex++;
            (*downloadNext)();
        });
    };

    (*downloadNext)();
}

void MainWindow::checkForUpdates() {
    // Check main update from GitHub raw URL of PyToolBox-Launcher
    QString branch = ConfigManager::instance().updateBranch();
    QString url = "https://raw.githubusercontent.com/CaptainBoots/Project-Proto/" + branch + "/PyToolBox-Launcher/PyToolBox-Launcher.py";

    QNetworkRequest request((QUrl(url)));
    QNetworkReply* reply = m_networkManager->get(request);
    
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        if (reply->error() == QNetworkReply::NoError) {
            QString content = reply->readAll();
            // Search version string
            QRegularExpression re("VERSION\\s*=\\s*['\"]([^'\"]+)['\"]");
            QRegularExpressionMatch match = re.match(content);
            if (match.hasMatch()) {
                QString remoteVer = match.captured(1);
                QString localVer = ConfigManager::instance().version();
                qDebug() << "Local Launcher Version:" << localVer << "Remote Launcher Version:" << remoteVer;
                
                // Compare versions (e.g. 1.0.1 vs 1.0.2)
                QStringList localParts = localVer.split(".");
                QStringList remoteParts = remoteVer.split(".");
                bool newer = false;
                for (int i = 0; i < qMin(localParts.size(), remoteParts.size()); ++i) {
                    int l = localParts[i].toInt();
                    int r = remoteParts[i].toInt();
                    if (r > l) {
                        newer = true;
                        break;
                    } else if (l > r) {
                        break;
                    }
                }

                if (newer) {
                    m_footerLabel->setText("Update available!");
                    
                    QMessageBox msgBox(this);
                    msgBox.setWindowTitle("Update Available");
                    msgBox.setText(QString("A new version of CToolBox-Launcher (v%1) is available.").arg(remoteVer));
                    msgBox.setInformativeText("Would you like to update automatically now, or open the GitHub releases page to download manually?");
                    
                    QPushButton* autoBtn = msgBox.addButton("Auto-Update", QMessageBox::AcceptRole);
                    QPushButton* manualBtn = msgBox.addButton("Manual (GitHub)", QMessageBox::ActionRole);
                    QPushButton* cancelBtn = msgBox.addButton("Cancel", QMessageBox::RejectRole);
                    
                    msgBox.setDefaultButton(autoBtn);
                    msgBox.exec();
                    
                    if (msgBox.clickedButton() == autoBtn) {
                        startAutoUpdate(remoteVer);
                    } else if (msgBox.clickedButton() == manualBtn) {
                        QDesktopServices::openUrl(QUrl("https://github.com/CaptainBoots/Project-Proto/releases"));
                    }
                } else {
                    m_footerLabel->setText("Up to date");
                }
            }
        }
        reply->deleteLater();
        
        // Next, load repository tree to scan script versions
        fetchRepoTree();
    });
}

void MainWindow::startAutoUpdate(const QString& remoteVer) {
    QString url = QString("https://github.com/CaptainBoots/Project-Proto/releases/download/v%1/CToolBox-Launcher-Portable.zip").arg(remoteVer);
    
    QNetworkRequest request((QUrl(url)));
    // Follow redirects since GitHub releases URLs redirect to AWS S3
    request.setAttribute(QNetworkRequest::RedirectPolicyAttribute, QNetworkRequest::NoLessSafeRedirectPolicy);
    
    QNetworkReply* reply = m_networkManager->get(request);
    
    QProgressDialog* progress = new QProgressDialog("Downloading update...", "Cancel", 0, 100, this);
    progress->setWindowModality(Qt::WindowModal);
    progress->setWindowTitle("Updating CToolBox");
    progress->setAutoClose(true);
    progress->setMinimumDuration(0); // show immediately
    
    connect(reply, &QNetworkReply::downloadProgress, this, [progress](qint64 bytesReceived, qint64 bytesTotal) {
        if (bytesTotal > 0) {
            progress->setMaximum(bytesTotal);
            progress->setValue(bytesReceived);
        }
    });
    
    connect(progress, &QProgressDialog::canceled, this, [reply]() {
        reply->abort();
    });
    
    connect(reply, &QNetworkReply::finished, this, [this, reply, progress]() {
        progress->close();
        progress->deleteLater();
        
        if (reply->error() == QNetworkReply::NoError) {
            QString appDir = QCoreApplication::applicationDirPath();
            QString zipPath = QDir(appDir).filePath("update.zip");
            
            QFile file(zipPath);
            if (file.open(QIODevice::WriteOnly)) {
                file.write(reply->readAll());
                file.close();
                
                m_footerLabel->setText("Applying update...");
                ConsoleWindow::appendLog("[Auto-Update] Download completed. Launching update script.\n");
                
                #ifdef Q_OS_WIN
                // Escape single quotes in path if present (e.g. "Boot's-ToolBox")
                QString appDirNative = QDir::toNativeSeparators(appDir).replace("'", "''");
                qint64 myPid = QCoreApplication::applicationPid();
                
                QString psCmd = QString(
                    "$pidToWait = %1; "
                    "$appDir = '%2'; "
                    "$zipPath = '%2\\update.zip'; "
                    "$timeout = 100; "
                    "while ((Get-Process -Id $pidToWait -ErrorAction SilentlyContinue) -and ($timeout -gt 0)) { "
                        "Start-Sleep -Milliseconds 100; "
                        "$timeout--; "
                    "} "
                    "Start-Sleep -Milliseconds 500; "
                    "$extracted = $false; "
                    "for ($retry = 0; $retry -lt 5; $retry++) { "
                        "try { "
                            "Expand-Archive -LiteralPath $zipPath -DestinationPath $appDir -Force -ErrorAction Stop; "
                            "$extracted = $true; "
                            "break; "
                        "} catch { "
                            "Start-Sleep -Seconds 1; "
                        "} "
                    "} "
                    "if ($extracted) { "
                        "Remove-Item -LiteralPath $zipPath -Force -ErrorAction SilentlyContinue; "
                        "Start-Process (Join-Path $appDir 'CToolBox-Launcher.exe'); "
                    "} else { "
                        "try { "
                            "[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null; "
                            "[System.Windows.Forms.MessageBox]::Show('Failed to extract CToolBox update. Please extract update.zip manually.', 'Update Error', 0, 16); "
                        "} catch {} "
                    "}"
                ).arg(QString::number(myPid), appDirNative);
                
                bool ok = QProcess::startDetached("powershell.exe", {"-NoProfile", "-Command", psCmd});
                if (ok) {
                    qApp->quit();
                } else {
                    QMessageBox::critical(this, "Update Error", "Failed to start updater helper process.");
                }
                #else
                QMessageBox::information(this, "Update Downloaded", "The update.zip has been downloaded to your application folder. Please extract it manually on your platform.");
                #endif
            } else {
                QMessageBox::critical(this, "Update Error", "Could not write the update file to disk. Check permissions.");
            }
        } else if (reply->error() != QNetworkReply::OperationCanceledError) {
            QMessageBox::critical(this, "Update Error", "Failed to download update: " + reply->errorString());
        }
        
        reply->deleteLater();
    });
}

void MainWindow::fetchRepoTree() {
    QString branch = ConfigManager::instance().updateBranch();
    QString url = "https://api.github.com/repos/CaptainBoots/Nova-Tools/git/trees/" + branch + "?recursive=1";

    QNetworkRequest request((QUrl(url)));
    request.setHeader(QNetworkRequest::UserAgentHeader, "CToolBox-Launcher-Cpp");
    request.setRawHeader("Accept", "application/vnd.github+json");

    QNetworkReply* reply = m_networkManager->get(request);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        if (reply->error() == QNetworkReply::NoError) {
            QJsonDocument doc = QJsonDocument::fromJson(reply->readAll());
            if (doc.isObject()) {
                QJsonObject root = doc.object();
                QJsonArray tree = root["tree"].toArray();
                m_gitTreePaths.clear();
                for (const auto& item : tree) {
                    QJsonObject itemObj = item.toObject();
                    if (itemObj["type"].toString() == "blob") {
                        m_gitTreePaths.append(itemObj["path"].toString());
                    }
                }
                m_treeFetched = true;
                ConsoleWindow::appendLog(QString("[Tree] Successfully fetched %1 files from remote repository.\n").arg(m_gitTreePaths.size()));
                
                // Discover missing tools from the remote tree
                QVector<ManagedScript> currentScripts = ConfigManager::instance().managedScripts();
                bool changed = false;

                QSet<QString> existingFilenames;
                for (const auto& s : currentScripts) {
                    existingFilenames.insert(s.filename);
                }

                for (const QString& path : m_gitTreePaths) {
                    QStringList parts = path.split("/");
                    if (parts.size() == 2 && parts[1] == "main.py") {
                        QString folderName = parts[0];
                        if (folderName == "LibreHardwareMonitor" || folderName == "configs" || folderName == "ToolBox Backup") {
                            continue;
                        }
                        
                        QString filename = folderName + "/main.py";
                        if (!existingFilenames.contains(filename)) {
                            // Discover a new core tool from remote!
                            ManagedScript s;
                            s.filename = filename;
                            
                            // Check if there is a cached label for this filename
                            QString cachedLabel = ConfigManager::instance().cachedLabels().value(filename);
                            if (!cachedLabel.isEmpty()) {
                                s.label = cachedLabel;
                            } else {
                                // Prettify folder name: replace hyphens/underscores with spaces
                                QString pretty = folderName;
                                pretty.replace("-", " ");
                                pretty.replace("_", " ");
                                s.label = pretty;
                            }
                            s.custom = false;
                            
                            ConfigManager::instance().addManagedScript(s);
                            changed = true;
                            ConsoleWindow::appendLog("[Discovery] Discovered remote core tool: " + s.label + "\n");
                        }
                    }
                }

                if (changed) {
                    ConfigManager::instance().save();
                    refreshMainButtons();
                }

                // Scan versions of local tools
                scanToolsVersions();
            }
        } else {
            ConsoleWindow::appendLog("[Tree Error] Failed to fetch remote repository tree: " + reply->errorString() + "\n");
        }
        reply->deleteLater();
    });
}

void MainWindow::scanToolsVersions() {
    if (!m_treeFetched) return;

    QVector<ManagedScript> scripts = ConfigManager::instance().managedScripts();
    
    struct ScanContext {
        int currentIdx = 0;
        QVector<ManagedScript> scripts;
        MainWindow* self;
    };

    auto context = std::make_shared<ScanContext>();
    context->scripts = scripts;
    context->self = this;

    auto scanNext = std::make_shared<std::function<void()>>();
    *scanNext = [context, scanNext]() {
        if (context->currentIdx >= context->scripts.size()) {
            context->self->refreshButtonLabels();
            return;
        }

        ManagedScript s = context->scripts[context->currentIdx];
        if (s.filename.endsWith(".exe") || s.custom) {
            context->currentIdx++;
            (*scanNext)();
            return;
        }

        QString localPath = QDir(ConfigManager::instance().toolsRootDir()).filePath(s.filename);
        if (!QFile::exists(localPath)) {
            context->self->m_toolStates[s.filename] = ToolState::Missing;
            context->currentIdx++;
            (*scanNext)();
            return;
        }

        // Fetch remote script version
        QString branch = ConfigManager::instance().updateBranch();
        QString url = "https://raw.githubusercontent.com/CaptainBoots/Nova-Tools/" + branch + "/" + s.filename;

        QNetworkReply* reply = context->self->m_networkManager->get(QNetworkRequest(QUrl(url)));
        connect(reply, &QNetworkReply::finished, context->self, [context, reply, s, scanNext]() {
            if (reply->error() == QNetworkReply::NoError) {
                QString remoteContent = reply->readAll();
                
                // Extract remote TOOL_ID or ID
                QString remoteId = "000000";
                QRegularExpression reId("(TOOL_ID|ID)\\s*=\\s*['\"]([^'\"]+)['\"]");
                QRegularExpressionMatch matchId = reId.match(remoteContent);
                if (matchId.hasMatch()) {
                    remoteId = matchId.captured(2);
                } else {
                    QRegularExpression reIdNum("(TOOL_ID|ID)\\s*=\\s*(\\d+)");
                    QRegularExpressionMatch matchIdNum = reIdNum.match(remoteContent);
                    if (matchIdNum.hasMatch()) {
                        remoteId = matchIdNum.captured(2);
                    }
                }
                remoteId = QString("%1").arg(remoteId.toInt(), 6, 10, QChar('0'));

                // SELF-HEALING RENAME CHECK:
                // Check if this remote ID matches an already discovered local tool, but the folder name has changed!
                if (remoteId != "000000") {
                    QVector<ManagedScript> currentScripts = ConfigManager::instance().managedScripts();
                    bool renamed = false;
                    for (int idx = 0; idx < currentScripts.size(); ++idx) {
                        ManagedScript& localScript = currentScripts[idx];
                        if (localScript.id == remoteId && localScript.filename != s.filename) {
                            // Folder renamed on GitHub!
                            QString oldFolder = localScript.filename.split("/")[0];
                            QString newFolder = s.filename.split("/")[0];
                            
                            QDir toolsDir(ConfigManager::instance().toolsRootDir());
                            QString oldPath = toolsDir.filePath(oldFolder);
                            QString newPath = toolsDir.filePath(newFolder);
                            
                            if (QDir(oldPath).exists()) {
                                if (QDir(newPath).exists()) {
                                    QDir(newPath).removeRecursively();
                                }
                                if (QDir().rename(oldPath, newPath)) {
                                    ConsoleWindow::appendLog(QString("[Self-Healing] Renamed local folder from '%1' to '%2'\n").arg(oldFolder).arg(newFolder));
                                }
                            }
                            
                            // Update the local script info in memory
                            localScript.filename = s.filename;
                            
                            // Extract pretty remote name if present
                            QRegularExpression reName("NAME\\s*=\\s*['\"]([^'\"]+)['\"]");
                            QRegularExpressionMatch matchName = reName.match(remoteContent);
                            if (matchName.hasMatch()) {
                                localScript.label = matchName.captured(1);
                            }
                            
                            renamed = true;
                        }
                    }
                    
                    if (renamed) {
                        ConfigManager::instance().setManagedScripts(currentScripts);
                        ConfigManager::instance().save();
                        // Rebuild main window buttons to match renames
                        QMetaObject::invokeMethod(context->self, "refreshMainButtons", Qt::QueuedConnection);
                    }
                }

                QRegularExpression re("VERSION\\s*=\\s*['\"]([^'\"]+)['\"]");
                QRegularExpressionMatch match = re.match(remoteContent);
                if (match.hasMatch()) {
                    QString remoteVer = match.captured(1);
                    
                    // Read local version
                    QString localPath = QDir(ConfigManager::instance().toolsRootDir()).filePath(s.filename);
                    QFile file(localPath);
                    QString localVer = "0.0.0";
                    if (file.open(QIODevice::ReadOnly | QIODevice::Text)) {
                        QTextStream in(&file);
                        QString localContent = in.readAll();
                        file.close();
                        QRegularExpressionMatch localMatch = re.match(localContent);
                        if (localMatch.hasMatch()) {
                            localVer = localMatch.captured(1);
                        }
                    }

                    // Compare versions
                    QStringList localParts = localVer.split(".");
                    QStringList remoteParts = remoteVer.split(".");
                    bool newer = false;
                    for (int i = 0; i < qMin(localParts.size(), remoteParts.size()); ++i) {
                        int l = localParts[i].toInt();
                        int r = remoteParts[i].toInt();
                        if (r > l) {
                            newer = true;
                            break;
                        } else if (l > r) {
                            break;
                        }
                    }

                    context->self->m_toolStates[s.filename] = newer ? ToolState::Update : ToolState::Current;
                }
            }
            reply->deleteLater();
            context->currentIdx++;
            (*scanNext)();
        });
    };

    (*scanNext)();
}

void MainWindow::launchLHM() {
    m_footerLabel->setText("Starting up Libre Hardware Monitor...");
    if (!ensureLHM()) {
        m_footerLabel->setText("Error preparing Libre Hardware Monitor");
        return;
    }

    patchLHMConfig();

    QString dest = QDir(ConfigManager::instance().toolsRootDir()).filePath("LibreHardwareMonitor/LibreHardwareMonitor.exe");
    dest = QDir::toNativeSeparators(dest);

#ifdef Q_OS_WIN
    // Launch with administrative privileges using ShellExecuteW
    wchar_t destW[1024];
    dest.toWCharArray(destW);
    destW[dest.length()] = 0;

    QString workingDir = QFileInfo(dest).absolutePath();
    wchar_t workingDirW[1024];
    workingDir.toWCharArray(workingDirW);
    workingDirW[workingDir.length()] = 0;

    HINSTANCE ret = ShellExecuteW(nullptr, L"runas", destW, nullptr, workingDirW, SW_SHOWNORMAL);
    if ((INT_PTR)ret <= 32) {
        m_footerLabel->setText("Error launching Libre Hardware Monitor");
        QMessageBox::critical(this, "Launch Error", QString("Elevation denied or runas failed. Ret Code: %1").arg((INT_PTR)ret));
    } else {
        m_footerLabel->setText("Ready");
        QMessageBox::information(this, "Libre Hardware Monitor", 
            "✓ LHM started successfully.\n\nIt will appear in your system tray shortly.\n"
            "The UAC prompt may have appeared behind this window.");
    }
#else
    bool ok = QProcess::startDetached(dest, {}, QFileInfo(dest).absolutePath());
    if (ok) {
        m_footerLabel->setText("Ready");
    } else {
        m_footerLabel->setText("Error launching Libre Hardware Monitor");
    }
#endif
}

bool MainWindow::ensureLHM() {
    QString toolsRoot = ConfigManager::instance().toolsRootDir();
    QString destExe = QDir(toolsRoot).filePath("LibreHardwareMonitor/LibreHardwareMonitor.exe");
    if (QFile::exists(destExe)) return true;

    QDir(toolsRoot).mkpath("LibreHardwareMonitor");
    
    // Download LibreHardwareMonitor zip file
    QString url = "https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases/latest/download/LibreHardwareMonitor.zip";
    QString zipPath = QDir(toolsRoot).filePath("LibreHardwareMonitor.zip");

    m_footerLabel->setText("Downloading LibreHardwareMonitor...");
    
    // Set up a nested event loop to make this synchronous for simple sequential execution
    QEventLoop loop;
    QNetworkReply* reply = m_networkManager->get(QNetworkRequest(QUrl(url)));
    connect(reply, &QNetworkReply::finished, &loop, &QEventLoop::quit);
    loop.exec();

    bool success = false;
    if (reply->error() == QNetworkReply::NoError) {
        QFile file(zipPath);
        if (file.open(QIODevice::WriteOnly)) {
            file.write(reply->readAll());
            file.close();
            success = true;
        }
    }
    reply->deleteLater();

    if (!success) {
        QMessageBox::critical(this, "Libre Hardware Monitor", "Failed to download Libre Hardware Monitor zip file.");
        return false;
    }

    // Decompress zip file using PowerShell Expand-Archive (robust & zero dependency on Windows!)
    QString destDir = QDir(toolsRoot).filePath("LibreHardwareMonitor");
    destDir = QDir::toNativeSeparators(destDir);
    zipPath = QDir::toNativeSeparators(zipPath);

#ifdef Q_OS_WIN
    QString cmd = QString("Expand-Archive -Path '%1' -DestinationPath '%2' -Force").arg(zipPath, destDir);
    int exitCode = QProcess::execute("powershell", {"-NoProfile", "-Command", cmd});
    if (exitCode == 0) {
        QFile::remove(zipPath);
        ConsoleWindow::appendLog("[LHM] Successfully downloaded and decompressed LHM zip.\n");
        return true;
    } else {
        QMessageBox::critical(this, "Libre Hardware Monitor", "Failed to extract Libre Hardware Monitor zip package.");
        return false;
    }
#else
    return false;
#endif
}

void MainWindow::patchLHMConfig() {
    QString configPath = QDir(ConfigManager::instance().toolsRootDir()).filePath("LibreHardwareMonitor/LibreHardwareMonitor.config");
    
    // Create simple LHM configuration XML if not exists
    if (!QFile::exists(configPath)) {
        QFile file(configPath);
        if (file.open(QIODevice::WriteOnly | QIODevice::Text)) {
            QTextStream out(&file);
            out << "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n";
            out << "<configuration>\n";
            out << "  <appSettings>\n";
            out << "    <add key=\"runWebServerMenuItem\" value=\"true\" />\n";
            out << "    <add key=\"startMinMenuItem\" value=\"value\" />\n";
            out << "  </appSettings>\n";
            out << "</configuration>\n";
            file.close();
        }
        return;
    }

    // Read and patch existing config
    QFile file(configPath);
    if (file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        QTextStream in(&file);
        QString content = in.readAll();
        file.close();

        // Use QRegularExpression to set the desired configuration properties
        QRegularExpression reWeb("<add key=\"runWebServerMenuItem\" value=\"([^\"]+)\" />");
        QRegularExpression reMin("<add key=\"startMinMenuItem\" value=\"([^\"]+)\" />");

        if (content.contains(reWeb)) {
            content.replace(reWeb, "<add key=\"runWebServerMenuItem\" value=\"true\" />");
        } else {
            content.replace("<appSettings>", "<appSettings>\n    <add key=\"runWebServerMenuItem\" value=\"true\" />");
        }

        if (content.contains(reMin)) {
            content.replace(reMin, "<add key=\"startMinMenuItem\" value=\"true\" />");
        } else {
            content.replace("<appSettings>", "<appSettings>\n    <add key=\"startMinMenuItem\" value=\"true\" />");
        }

        if (file.open(QIODevice::WriteOnly | QIODevice::Text)) {
            QTextStream out(&file);
            out << content;
            file.close();
            ConsoleWindow::appendLog("[LHM] Configuration patched successfully (web server & minimised options enabled).\n");
        }
    }
}

void MainWindow::openConsole() {
    ConsoleWindow* console = new ConsoleWindow(this);
    console->setWindowModality(Qt::NonModal);
    console->show();
}
