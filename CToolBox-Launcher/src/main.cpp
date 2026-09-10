#include <QApplication>
#include <QIcon>
#include <QDir>
#include <QFile>
#include <QProcess>
#include <QDialog>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QTextEdit>
#include <QLabel>
#include <QPushButton>
#include <QClipboard>
#include <QMessageBox>
#include "mainwindow.h"
#include "customwidgets.h"

#ifdef Q_OS_WIN
#include <windows.h>
#include <shellapi.h>
#endif

// Custom Qt message handler to redirect all logs to our ConsoleWindow
void customMessageHandler(QtMsgType type, const QMessageLogContext& context, const QString& msg) {
    QString txt;
    switch (type) {
    case QtDebugMsg:
        txt = QString("[Debug] %1").arg(msg);
        break;
    case QtInfoMsg:
        txt = QString("[Info] %1").arg(msg);
        break;
    case QtWarningMsg:
        txt = QString("[Warning] %1 (Line %2 in %3)").arg(msg).arg(context.line).arg(context.file);
        break;
    case QtCriticalMsg:
        txt = QString("[Critical] %1 (Line %2 in %3)").arg(msg).arg(context.line).arg(context.file);
        break;
    case QtFatalMsg:
        txt = QString("[Fatal] %1 (Line %2 in %3)").arg(msg).arg(context.line).arg(context.file);
        break;
    }
    
    QString formatted = QString("%1\n").arg(txt);
    
    // Append to static console window logs buffer
    ConsoleWindow::appendLog(formatted);
    
    // Also output to original standard error for debugging
    fprintf(stderr, "%s", formatted.toUtf8().constData());
    fflush(stderr);
    
    if (type == QtFatalMsg) {
        abort();
    }
}

int main(int argc, char* argv[]) {
    // Enable High DPI scaling
    QGuiApplication::setHighDpiScaleFactorRoundingPolicy(Qt::HighDpiScaleFactorRoundingPolicy::PassThrough);

    // Check if we should run as the core application
    bool runCore = false;
    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--run-core") == 0) {
            runCore = true;
            break;
        }
    }

    if (!runCore) {
        // Run as the Supervisor Process
        QApplication app(argc, argv);
        
        QString program = QString::fromUtf8(argv[0]);
        QStringList arguments;
        arguments << "--run-core";
        for (int i = 1; i < argc; ++i) {
            arguments << QString::fromUtf8(argv[i]);
        }
        
        QProcess process;
        process.setProcessChannelMode(QProcess::MergedChannels); // merge stdout and stderr
        process.start(program, arguments);
        
        process.waitForFinished(-1);
        
        int exitCode = process.exitCode();
        QProcess::ExitStatus exitStatus = process.exitStatus();
        
        if (exitCode != 0 || exitStatus == QProcess::CrashExit) {
            QString errorLog = process.readAllStandardOutput();
            if (errorLog.isEmpty()) {
                errorLog = "The application process exited with error or crashed but produced no output.";
            }
            
            QDialog dialog;
            dialog.setWindowTitle("CToolBox-Launcher - Diagnostic Crash Console");
            dialog.resize(700, 480);
            dialog.setStyleSheet(
                "QDialog { background-color: #0f0f13; }"
                "QLabel { color: #ff4b72; font-family: 'Consolas'; font-size: 14px; font-weight: bold; }"
                "QTextEdit { background-color: #1f102a; color: #e2e0f0; font-family: 'Consolas'; font-size: 11px; border: 1px solid #2a2a38; }"
                "QPushButton { background-color: #2a2a38; color: #e2e0f0; font-family: 'Consolas'; font-size: 12px; font-weight: bold; border: none; padding: 8px 16px; }"
                "QPushButton:hover { background-color: #7c5cfc; }"
            );
            
            QVBoxLayout* layout = new QVBoxLayout(&dialog);
            layout->setContentsMargins(20, 20, 20, 20);
            layout->setSpacing(10);
            
            QLabel* titleLabel = new QLabel("⚠️ Application Crash / Startup Failure Detected", &dialog);
            titleLabel->setAlignment(Qt::AlignCenter);
            layout->addWidget(titleLabel);
            
            QLabel* descLabel = new QLabel("The application failed to start or crashed. Diagnostic logs are shown below:", &dialog);
            descLabel->setStyleSheet("color: #e2e0f0; font-size: 12px; font-weight: normal;");
            descLabel->setAlignment(Qt::AlignCenter);
            layout->addWidget(descLabel);
            
            QTextEdit* textEdit = new QTextEdit(&dialog);
            textEdit->setReadOnly(true);
            textEdit->setPlainText(errorLog);
            layout->addWidget(textEdit, 1);
            
            QHBoxLayout* btnLayout = new QHBoxLayout();
            QPushButton* copyBtn = new QPushButton("Copy Logs to Clipboard", &dialog);
            copyBtn->setCursor(Qt::PointingHandCursor);
            QObject::connect(copyBtn, &QPushButton::clicked, [&]() {
                QGuiApplication::clipboard()->setText(errorLog);
                QMessageBox::information(&dialog, "Copied", "Diagnostic logs copied to clipboard!");
            });
            
            QPushButton* closeBtn = new QPushButton("Close Console", &dialog);
            closeBtn->setCursor(Qt::PointingHandCursor);
            closeBtn->setStyleSheet("QPushButton { background-color: #9D00FF; color: #0f0f13; } QPushButton:hover { background-color: #b44bff; }");
            QObject::connect(closeBtn, &QPushButton::clicked, &dialog, &QDialog::accept);
            
            btnLayout->addWidget(copyBtn);
            btnLayout->addStretch(1);
            btnLayout->addWidget(closeBtn);
            
            layout->addLayout(btnLayout);
            
            dialog.exec();
            return exitCode == 0 ? 1 : exitCode;
        }
        return 0;
    }

    // Run as the Core Process - filter out --run-core from command line args
    int newArgc = 0;
    char** newArgv = new char*[argc];
    for (int i = 0; i < argc; ++i) {
        if (strcmp(argv[i], "--run-core") != 0) {
            newArgv[newArgc++] = argv[i];
        }
    }

    QApplication app(newArgc, newArgv);
    app.setApplicationName("CToolBox-Launcher");
    app.setApplicationVersion(ConfigManager::instance().version());

    // Register windows process ID for taskbar grouping
#ifdef Q_OS_WIN
    typedef HRESULT(WINAPI* SetCurrentProcessExplicitAppUserModelIDFunc)(PCWSTR);
    HMODULE shell32 = LoadLibraryW(L"shell32.dll");
    if (shell32) {
        auto setAppId = (SetCurrentProcessExplicitAppUserModelIDFunc)GetProcAddress(shell32, "SetCurrentProcessExplicitAppUserModelID");
        if (setAppId) {
            setAppId(L"CaptainBoots.CToolBox-Launcher.1.0.1");
        }
        FreeLibrary(shell32);
    }
#endif

    // Setup custom message handler
    qInstallMessageHandler(customMessageHandler);

    qDebug() << "CToolBox-Launcher starting up...";
    qDebug() << "Version:" << ConfigManager::instance().version();

    // Set Window Icon
    QString iconPath = QDir(QCoreApplication::applicationDirPath()).filePath("Images/Boot's-ToolBox-256.ico");
    if (!QFile::exists(iconPath)) {
        iconPath = QDir(QCoreApplication::applicationDirPath() + "/../Images/Boot's-ToolBox-256.ico").canonicalPath();
    }
    if (QFile::exists(iconPath)) {
        app.setWindowIcon(QIcon(iconPath));
        qDebug() << "[Process] Loaded application icon from:" << iconPath;
    }

    MainWindow mainWin;
    if (QFile::exists(iconPath)) {
        mainWin.setWindowIcon(QIcon(iconPath));
    }
    mainWin.show();

    int ret = app.exec();
    delete[] newArgv;
    return ret;
}
