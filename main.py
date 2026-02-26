import os
import sys
import shutil
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget,
    QSplitter, QFileDialog, QMessageBox, QTreeView, QTabWidget,
    QToolBar, QInputDialog, QMenu
)
from PyQt6.QtGui import QFont, QAction, QColor, QFileSystemModel, QIcon, QTextCursor
from PyQt6.QtCore import Qt, QDir, QUrl, QProcess
from PyQt6.Qsci import QsciScintilla, QsciLexerCustom

# --- Themes ---
THEMES = {
    "dark": {
        "bg": "#1e1e1e", "fg": "#cccccc", "tree_bg": "#252526",
        "tree_hover": "#2a2d2e", "tree_sel": "#37373d",
        "menu_bg": "#3c3c3c", "menu_sel": "#505050",
        "border": "#3e3e42",
        "editor_bg": "#1e1e1e", "editor_fg": "#d4d4d4",
        "margin_fg": "#858585", "sel_bg": "#264f78",
        "kw_color": "#569cd6", "str_color": "#ce9178", "cmt_color": "#6a9955"
    },
    "light": {
        "bg": "#f3f3f3", "fg": "#333333", "tree_bg": "#f3f3f3",
        "tree_hover": "#e8e8e8", "tree_sel": "#d4d4d4",
        "menu_bg": "#e8e8e8", "menu_sel": "#d4d4d4",
        "border": "#cccccc",
        "editor_bg": "#ffffff", "editor_fg": "#333333",
        "margin_fg": "#999999", "sel_bg": "#add6ff",
        "kw_color": "#0000ff", "str_color": "#a31515", "cmt_color": "#008000"
    }
}

def get_stylesheet(theme_name):
    t = THEMES[theme_name]
    return f"""
    QMainWindow {{ background-color: {t['bg']}; color: {t['fg']}; }}
    QTreeView {{ background-color: {t['tree_bg']}; color: {t['fg']}; border: none; }}
    QTreeView::item:hover {{ background-color: {t['tree_hover']}; }}
    QTreeView::item:selected {{ background-color: {t['tree_sel']}; }}
    QTextEdit {{ background-color: {t['editor_bg']}; color: {t['editor_fg']}; border: none; selection-background-color: {t['sel_bg']}; }}
    QSplitter::handle {{ background-color: {t['border']}; }}
    QSplitter::handle:vertical {{ height: 1px; }}
    QSplitter::handle:horizontal {{ width: 1px; }}
    QMenuBar {{ background-color: {t['menu_bg']}; color: {t['fg']}; }}
    QMenuBar::item:selected {{ background-color: {t['menu_sel']}; }}
    QMenu {{ background-color: {t['tree_bg']}; color: {t['fg']}; border: 1px solid {t['border']}; }}
    QMenu::item:selected {{ background-color: {t['sel_bg']}; }}
    QMessageBox {{ background-color: {t['bg']}; color: {t['fg']}; }}
    QTabWidget::pane {{ border: 1px solid {t['border']}; }}
    QTabBar::tab {{ background: {t['tree_bg']}; color: {t['margin_fg']}; padding: 8px 15px; border: none; border-right: 1px solid {t['border']}; }}
    QTabBar::tab:selected {{ background: {t['editor_bg']}; color: {t['fg']}; border-top: 2px solid #007acc; }}
    QToolBar {{ background: {t['menu_bg']}; border: none; padding: 2px; }}
    """

# --- Lexer ---
class MADLexer(QsciLexerCustom):
    def __init__(self, theme_name, parent=None):
        super().__init__(parent)
        t = THEMES[theme_name]
        self.setDefaultColor(QColor(t["editor_fg"]))
        self.setDefaultPaper(QColor(t["editor_bg"]))
        self.setDefaultFont(QFont("Courier", 12))
        
        self.STYLE_DEFAULT = 0
        self.STYLE_KEYWORD = 1
        self.STYLE_STRING = 2
        self.STYLE_COMMENT = 3
        
        self.setColor(QColor(t["editor_fg"]), self.STYLE_DEFAULT)
        self.setColor(QColor(t["kw_color"]), self.STYLE_KEYWORD)
        self.setColor(QColor(t["str_color"]), self.STYLE_STRING)
        self.setColor(QColor(t["cmt_color"]), self.STYLE_COMMENT)
        
        self.keywords = [
            "NORMAL", "MODE", "IS", "INTEGER", "ENTRY", "TO", "W'R", "T'O", 
            "O'E", "E'L", "T'H", "FOR", "F'N", "E'N", "PRINT", "COMMENT", 
            "EXTERNAL", "FUNCTION", "DIMENSION", "EXECUTE", "RETURN"
        ]

    def description(self, style):
        if style == self.STYLE_DEFAULT: return "Default"
        if style == self.STYLE_KEYWORD: return "Keyword"
        if style == self.STYLE_STRING: return "String"
        if style == self.STYLE_COMMENT: return "Comment"
        return ""

    def styleText(self, start, end):
        self.startStyling(start)
        text = self.editor().text()[start:end]
        i = 0
        while i < len(text):
            if text[i] == '$':
                length = 1
                i += 1
                while i < len(text) and text[i] != '$': length, i = length + 1, i + 1
                if i < len(text): length, i = length + 1, i + 1
                self.setStyling(length, self.STYLE_STRING)
                continue
            if text[i].isalpha() or text[i] == "'":
                word, length = "", 0
                while i < len(text) and (text[i].isalnum() or text[i] == "'"):
                    word += text[i]
                    length, i = length + 1, i + 1
                if word.upper() in self.keywords: self.setStyling(length, self.STYLE_KEYWORD)
                else: self.setStyling(length, self.STYLE_DEFAULT)
                continue
            self.setStyling(1, self.STYLE_DEFAULT)
            i += 1

# --- Main App ---
class MadIDE(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_theme = "dark"
        self.open_files = {} # path -> editor_widget
        self.build_process = None
        self.resize(1100, 750)
        self.setWindowTitle("MAD IDE")
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.create_toolbar()
        self.create_menu_bar()
        
        # Horizontal Splitter (Sidebar | Work Area)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 1. Sidebar Explorer
        self.setup_explorer()
        self.main_splitter.addWidget(self.tree_view)
        
        # 2. Work Area (Vertical Splitter: Editor | Panel)
        self.work_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Editor Tabs
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.work_splitter.addWidget(self.tabs)
        
        # Bottom Panel Tabs (Console | Terminal)
        self.bottom_tabs = QTabWidget()
        self.console = QTextEdit()
        self.console.setFont(QFont("Courier", 11))
        self.console.setReadOnly(True)
        self.bottom_tabs.addTab(self.console, "Output Console")
        
        # Terminal mock native
        self.terminal = QTextEdit()
        self.terminal.setFont(QFont("Courier", 11))
        self.terminal.setReadOnly(True)
        self.terminal.append(f"MAD Terminal V1.0\n---\n[Mock] Current directory: {os.getcwd()}\nRun external terminal commands here in the future.\n> ")
        self.bottom_tabs.addTab(self.terminal, "Terminal (Ctrl+~)")
        
        self.work_splitter.addWidget(self.bottom_tabs)
        self.work_splitter.setSizes([int(self.height() * 0.70), int(self.height() * 0.30)])
        
        self.main_splitter.addWidget(self.work_splitter)
        self.main_splitter.setSizes([int(self.width() * 0.2), int(self.width() * 0.8)])
        self.main_layout.addWidget(self.main_splitter)
        
        self.apply_theme()
        self.new_file() # Start with an untitled tab
        self.run_startup_checks()

    def run_startup_checks(self):
        self.log("--- System Checks ---")
        make_found = shutil.which("make")
        gcc_found = shutil.which("gcc")
        clang_found = shutil.which("clang")
        
        if make_found:
            self.log(f"[OK] 'make' found at: {make_found}")
        else:
            self.log("[ERROR] 'make' is missing! You will not be able to build the MAD compiler.")
            
        if gcc_found:
            self.log(f"[OK] 'gcc' found at: {gcc_found}")
        elif clang_found:
            self.log(f"[OK] 'clang' found at: {clang_found}")
        else:
            self.log("[WARNING] No C compiler (gcc/clang) found in system PATH.")
        self.log("---------------------\n")

    def setup_explorer(self):
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath(QDir.rootPath())
        
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.file_model)
        self.tree_view.setRootIndex(self.file_model.index(os.getcwd()))
        for i in range(1, 4): self.tree_view.setColumnHidden(i, True)
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setAnimated(True)
        self.tree_view.setIndentation(20)
        self.tree_view.clicked.connect(self.on_tree_click)
        
        # Context Menu for explorer
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.explorer_context_menu)

    def explorer_context_menu(self, position):
        index = self.tree_view.indexAt(position)
        path = self.file_model.filePath(index) if index.isValid() else self.file_model.rootPath()
        if not os.path.isdir(path): path = os.path.dirname(path)
            
        menu = QMenu()
        new_file_act = menu.addAction("New File")
        new_folder_act = menu.addAction("New Folder")
        open_folder_act = menu.addAction("Open Project Folder")
        
        action = menu.exec(self.tree_view.viewport().mapToGlobal(position))
        
        if action == new_file_act:
            name, ok = QInputDialog.getText(self, "New File", "Enter file name:")
            if ok and name: open(os.path.join(path, name), 'w').close()
        elif action == new_folder_act:
            name, ok = QInputDialog.getText(self, "New Folder", "Enter folder name:")
            if ok and name: os.makedirs(os.path.join(path, name), exist_ok=True)
        elif action == open_folder_act:
            self.tree_view.setRootIndex(self.file_model.index(path))

    def create_editor_widget(self, text=""):
        editor = QsciScintilla()
        editor.setUtf8(True)
        editor.setFont(QFont("Courier", 12))
        editor.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        editor.setMarginWidth(0, "0000")
        
        t = THEMES[self.current_theme]
        editor.setPaper(QColor(t["editor_bg"]))
        editor.setColor(QColor(t["editor_fg"]))
        editor.setCaretForegroundColor(QColor(t["editor_fg"]))
        editor.setMarginsBackgroundColor(QColor(t["editor_bg"]))
        editor.setMarginsForegroundColor(QColor(t["margin_fg"]))
        editor.setSelectionBackgroundColor(QColor(t["sel_bg"]))
        
        lexer = MADLexer(self.current_theme, editor)
        editor.setLexer(lexer)
        editor.setText(text)
        return editor

    def create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        self.run_act = QAction("▶ Run", self)
        self.run_act.triggered.connect(self.run_current)
        toolbar.addAction(self.run_act)
        
        self.stop_act = QAction("⏹ Stop", self)
        self.stop_act.triggered.connect(self.kill_process)
        self.stop_act.setEnabled(False)
        toolbar.addAction(self.stop_act)
        
        theme_act = QAction("🌗 Toggle Theme", self)
        theme_act.triggered.connect(self.toggle_theme)
        toolbar.addAction(theme_act)
        
        term_act = QAction("💻 Terminal", self)
        term_act.setShortcut("Ctrl+`")
        term_act.triggered.connect(self.toggle_terminal)
        toolbar.addAction(term_act)

    def create_menu_bar(self):
        mb = self.menuBar()
        fm = mb.addMenu("File")
        for name, shortcut, slot in [("New", "Ctrl+N", self.new_file), ("Open", "Ctrl+O", self.open_file), 
                                     ("Save", "Ctrl+S", self.save_file), ("Save As...", "Ctrl+Shift+S", self.save_as),
                                     ("Open Folder", "Ctrl+K", self.open_folder), ("Exit", "Ctrl+Q", self.close)]:
            act = QAction(name, self)
            act.setShortcut(shortcut)
            act.triggered.connect(slot)
            fm.addAction(act)
            
        tm = mb.addMenu("Tools")
        build_act = QAction("Build MAD Compiler", self)
        build_act.setShortcut("Ctrl+B")
        build_act.triggered.connect(self.build_compiler)
        tm.addAction(build_act)
        
        rm = mb.addMenu("Run")
        self.menu_run_act = QAction("Run Application", self)
        self.menu_run_act.setShortcut("F5")
        self.menu_run_act.triggered.connect(self.run_current)
        rm.addAction(self.menu_run_act)
        
        self.menu_stop_act = QAction("Stop Application", self)
        self.menu_stop_act.setShortcut("Shift+F5")
        self.menu_stop_act.triggered.connect(self.kill_process)
        self.menu_stop_act.setEnabled(False)
        rm.addAction(self.menu_stop_act)

    def set_running_state(self, is_running):
        self.run_act.setEnabled(not is_running)
        self.menu_run_act.setEnabled(not is_running)
        self.stop_act.setEnabled(is_running)
        self.menu_stop_act.setEnabled(is_running)

    def kill_process(self):
        if hasattr(self, 'run_process') and self.run_process:
            self.run_process.kill()
        if hasattr(self, 'c_process') and self.c_process:
            self.c_process.kill()
        if hasattr(self, 'exec_process') and self.exec_process:
            self.exec_process.kill()
        self.log("\n[SYSTEM] Process forcefully stopped by user.")
        self.set_running_state(False)

    def build_compiler(self):
        # Prevent running multiple builds simultaneously
        if self.build_process and self.build_process.state() != QProcess.ProcessState.NotRunning:
            self.log("[WARNING] A build is already in progress!")
            return
            
        target_dir = os.path.join(os.getcwd(), "mad_compiler_src")
        if not os.path.exists(target_dir):
            self.log(f"[ERROR] Compiler source folder not found at {target_dir}. Make sure you run the setup_compiler.py script.")
            return

        self.bottom_tabs.show()
        self.bottom_tabs.setCurrentWidget(self.console)
        self.log(f"\n[SYSTEM] Starting MAD Compiler Build in {target_dir}...")
        
        self.build_process = QProcess(self)
        self.build_process.setWorkingDirectory(target_dir)
        
        # Connect signals for real-time output
        self.build_process.readyReadStandardOutput.connect(self.handle_stdout)
        self.build_process.readyReadStandardError.connect(self.handle_stderr)
        self.build_process.finished.connect(self.process_finished)
        
        self.build_process.start("make")

    def handle_stdout(self):
        data = self.build_process.readAllStandardOutput()
        text = bytes(data).decode("utf8", errors="ignore")
        self.log(text.strip(), new_line=False)

    def handle_stderr(self):
        data = self.build_process.readAllStandardError()
        text = bytes(data).decode("utf8", errors="ignore")
        self.log(f"[ERROR] {text.strip()}", new_line=False)

    def process_finished(self, exit_code, exit_status):
        if exit_status == QProcess.ExitStatus.NormalExit and exit_code == 0:
            self.log("\n[SUCCESS] Build finished successfully! Compiler is ready.")
        else:
            self.log(f"\n[FAILURE] Build failed with exit code: {exit_code}")
        self.build_process = None

    def apply_theme(self):
        self.setStyleSheet(get_stylesheet(self.current_theme))
        t = THEMES[self.current_theme]
        self.console.setStyleSheet(f"background-color: {t['editor_bg']}; color: {t['margin_fg']};")
        # Re-apply theme to all open tabs
        for i in range(self.tabs.count()):
            editor = self.tabs.widget(i)
            editor.setPaper(QColor(t["editor_bg"]))
            editor.setColor(QColor(t["editor_fg"]))
            editor.setCaretForegroundColor(QColor(t["editor_fg"]))
            editor.setMarginsBackgroundColor(QColor(t["editor_bg"]))
            editor.setMarginsForegroundColor(QColor(t["margin_fg"]))
            editor.setSelectionBackgroundColor(QColor(t["sel_bg"]))
            editor.setLexer(MADLexer(self.current_theme, editor))

    def toggle_theme(self):
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self.apply_theme()

    def toggle_terminal(self):
        if self.bottom_tabs.isVisible(): self.bottom_tabs.hide()
        else:
            self.bottom_tabs.show()
            self.bottom_tabs.setCurrentWidget(self.terminal)

    def on_tree_click(self, index):
        path = self.file_model.filePath(index)
        if os.path.isfile(path): self.open_file_path(path)

    def open_file_path(self, path):
        if path in self.open_files:
            self.tabs.setCurrentWidget(self.open_files[path])
            return
        try:
            with open(path, 'r') as f: content = f.read()
            editor = self.create_editor_widget(content)
            self.open_files[path] = editor
            idx = self.tabs.addTab(editor, os.path.basename(path))
            self.tabs.setCurrentIndex(idx)
        except Exception as e:
            self.log(f"Error opening {path}: {e}")

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Open Project Folder")
        if folder: self.tree_view.setRootIndex(self.file_model.index(folder))

    def new_file(self):
        if not hasattr(self, 'untitled_count'): self.untitled_count = 0
        self.untitled_count += 1
        editor = self.create_editor_widget()
        editor.setModified(False)
        idx = self.tabs.addTab(editor, f"Untitled-{self.untitled_count}")
        self.tabs.setCurrentIndex(idx)

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "MAD Files (*.mad);;All Files (*)")
        if path: self.open_file_path(path)

    def save_file(self):
        editor = self.tabs.currentWidget()
        if not editor: return
        path = next((p for p, e in self.open_files.items() if e == editor), None)
        if path:
            with open(path, 'w') as f: f.write(editor.text())
            editor.setModified(False)
            self.tabs.setTabText(self.tabs.currentIndex(), os.path.basename(path))
            self.log(f"Saved {path}")
        else: self.save_as()

    def save_as(self):
        editor = self.tabs.currentWidget()
        if not editor: return
        path, _ = QFileDialog.getSaveFileName(self, "Save File As", "", "MAD Files (*.mad);;All Files (*)")
        if path:
            with open(path, 'w') as f: f.write(editor.text())
            self.open_files[path] = editor
            editor.setModified(False)
            self.tabs.setTabText(self.tabs.currentIndex(), os.path.basename(path))
            self.log(f"Saved {path}")

    def close_tab(self, index):
        editor = self.tabs.widget(index)
        
        if editor.isModified():
            path = next((p for p, e in self.open_files.items() if e == editor), self.tabs.tabText(index))
            name = os.path.basename(path)
            reply = QMessageBox.question(
                self, 'Save Changes',
                f'Do you want to save changes to {name} before closing?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.tabs.setCurrentIndex(index)
                self.save_file()
                if editor.isModified(): return # Cancelled save
            elif reply == QMessageBox.StandardButton.Cancel:
                return
                
        self.tabs.removeTab(index)
        path = next((p for p, e in self.open_files.items() if e == editor), None)
        if path: del self.open_files[path]

    def run_current(self):
        self.bottom_tabs.show()
        self.bottom_tabs.setCurrentWidget(self.console)
        editor = self.tabs.currentWidget()
        if not editor:
            self.log("[ERROR] No file open to compile.")
            return

        # 1. Require a saved file to compile
        path = next((p for p, e in self.open_files.items() if e == editor), None)
        if not path:
            self.log("[SYSTEM] Unsaved file. Please save before running.")
            self.save_as()
            # Check if user actually saved it
            path = next((p for p, e in self.open_files.items() if e == editor), None)
            if not path:
                self.log("[SYSTEM] Run aborted. File not saved.")
                return
        else:
            # Apply CTSS Abbreviation Expansion and MAD Syntax Preprocessor
            ctss_replacements = {
                r"\bW'R\b": "WHENEVER",
                r"\bO'R\b": "OR WHENEVER",
                r"\bO'E\b": "OTHERWISE",
                r"\bE'L\b": "END OF CONDITIONAL",
                r"\bT'O\b": "TRANSFER TO",
                r"\bT'H\b": "THROUGH",
                r"\bF'N\b": "FUNCTION RETURN",
                r"\bV'S\b": "VECTOR VALUES",
                r"\bE'M\b": "END OF PROGRAM",
                r"\bE'N\b": "END OF FUNCTION",
                r"\bR\b": "PRINT COMMENT"
            }
            
            raw_text = editor.text()
            for abbrev, full in ctss_replacements.items():
                raw_text = __import__('re').sub(abbrev, full, raw_text)
            
            raw_lines = raw_text.split('\n')
            mad_keywords = {
                "BOOLEAN", "CONDITIONAL", "CONTINUE", "DATA", "DIMENSION",
                "BACKSPACE_RECORD_OF_TAPE", "END_OF_FILE_TAPE", "END", "ENTRY",
                "ERASABLE", "ERROR_RETURN", "EXECUTE", "EXTERNAL", "FLOATING_POINT",
                "FOR", "FORMAT_VARIABLE", "FUNCTION", "FUNCTION_RETURN", "INTEGER",
                "INTERNAL", "IS", "MODE", "NORMAL", "OF", "OR", "OTHERWISE",
                "PARAMETER", "PAUSE", "PRINT_COMMENT", "PRINT_FORMAT",
                "PRINT_ONLINE_FORMAT", "PRINT_RESULTS", "PROGRAM", "PROGRAM_COMMON",
                "READ_DATA", "READ_AND_PRINT_DATA", "READ_BCD_TAPE",
                "READ_BINARY_TAPE", "READ_FORMAT", "REWIND_TAPE", "RESTORE",
                "RESTORE_RETURN", "SAVE", "SAVE_RETURN", "SET_LIST_TO",
                "STATEMENT_LABEL", "THROUGH", "TO", "TRANSFER", "VALUES",
                "VECTOR", "WHENEVER", "WRITE_BCD_TAPE", "WRITE_BINARY_TAPE",
                "UNLOAD_TAPE", "INSERT_FILE", "COMMENT", "DOTRANGE",
                "SET", "FORMAT", "FLOATING", "PRINT",
                "V'S", "W'R", "T'O", "O'E", "E'L", "F'N", "E'N"
            }
            
            processed_lines = []
            for line in raw_lines:
                stripped = line.strip()
                if not stripped:
                    processed_lines.append(line)
                    continue
                
                # If already manually padded to IBM 7090 spec (11 leading spaces)
                if len(line) - len(line.lstrip()) >= 11:
                    processed_lines.append(line)
                    continue
                
                parts = stripped.split(None, 1)
                if len(parts) == 1:
                    processed_lines.append("           " + stripped)
                    continue
                
                w1, w2 = parts[0], parts[1]
                w1_upper = w1.upper()
                
                # Detect if the first word is a Label
                has_label = False
                if w1_upper not in mad_keywords and w1.isalnum() and not w2.startswith("=") and not w2.startswith("("):
                    has_label = True
                
                if has_label:
                    # Pad label up to column 6, then space up to column 11!
                    lbl = w1[:6].ljust(11)
                    processed_lines.append(lbl + w2)
                else:
                    processed_lines.append("           " + stripped)
            
            formatted_code = '\n'.join(processed_lines)
            
            # Save preprocessed string to file
            with open(path, 'w') as f:
                f.write(formatted_code)
                
            # Render preprocessed string back onto Editor tab natively!
            editor.setText(formatted_code)
            self.log(f"[SYSTEM] Auto-padded & saved {path}")

        # 2. Check for compiler bin
        mad_bin = os.path.join(os.getcwd(), "mad_compiler_src", "mad")
        if sys.platform == "win32" and os.path.exists(mad_bin + ".exe"):
            mad_bin += ".exe"
            
        if not os.path.exists(mad_bin):
            self.log("\n[ERROR] MAD compiler binary not found. Please click 'Tools -> Build MAD Compiler' first.")
            return

        self.set_running_state(True)

        # Start Pipeline Step 1 (MAD -> C)
        self.console.clear()
        self.log(f"[STEP 1] Transpiling {os.path.basename(path)} to C...")
        self.current_compile_path = path  # Save state for step 2
        
        self.run_process = QProcess(self)
        self.run_process.setWorkingDirectory(os.path.dirname(path))
        self.run_process.readyReadStandardOutput.connect(self.handle_run_stdout)
        self.run_process.readyReadStandardError.connect(self.handle_run_stderr)
        self.run_process.finished.connect(self.step1_finished)
        
        # We must pass -S to force the compiler to stop at C and not delete the .c file
        self.run_process.start(mad_bin, ["-S", path])

    def handle_run_stdout(self):
        data = self.run_process.readAllStandardOutput()
        text = bytes(data).decode("utf8", errors="ignore")
        self.log(text.strip(), new_line=False)

    def handle_run_stderr(self):
        data = self.run_process.readAllStandardError()
        text = bytes(data).decode("utf8", errors="ignore")
        self.log(f"[MAD MSG] {text.strip()}", new_line=False)

    def step1_finished(self, exit_code, exit_status):
        if exit_status == QProcess.ExitStatus.NormalExit and exit_code == 0:
            self.log("\n[SUCCESS] Transpilation complete.")
            self.start_step2_c_compile()
        else:
            self.log(f"\n[FAILURE] MAD Compiler failed. (Exit code {exit_code})")
            self.set_running_state(False)
        self.run_process = None

    def start_step2_c_compile(self):
        base_name, _ = os.path.splitext(self.current_compile_path)
        c_file = base_name + ".c"
        out_ext = ".exe" if sys.platform == "win32" else ".out"
        bin_file = base_name + out_ext
        
        if not os.path.exists(c_file):
            self.log(f"\n[ERROR] Step 1 finished, but no generated .c file found at {c_file}")
            self.set_running_state(False)
            return
            
        # Determine C compiler
        c_compiler = shutil.which("gcc") or shutil.which("clang")
        if not c_compiler:
            self.log("\n[ERROR] No 'gcc' or 'clang' found on system PATH to build the binary.")
            self.set_running_state(False)
            return

        self.log(f"\n[STEP 2] Compiling {os.path.basename(c_file)} to binary ({out_ext})...")
        self.c_process = QProcess(self)
        self.c_process.setWorkingDirectory(os.path.dirname(self.current_compile_path))
        
        self.c_process.readyReadStandardOutput.connect(lambda: self.log(bytes(self.c_process.readAllStandardOutput()).decode("utf8", errors="ignore").strip(), new_line=False))
        self.c_process.readyReadStandardError.connect(lambda: self.log(f"[GCC ERROR] {bytes(self.c_process.readAllStandardError()).decode('utf8', errors='ignore').strip()}", new_line=False))
        self.c_process.finished.connect(lambda code, status: self.step2_finished(code, status, bin_file))
        
        self.c_process.start(c_compiler, [c_file, "-o", bin_file])
        
    def step2_finished(self, exit_code, exit_status, bin_file):
        if exit_status == QProcess.ExitStatus.NormalExit and exit_code == 0:
            self.log("\n[SUCCESS] Binary compiled successfully!")
            self.start_step3_run(bin_file)
        else:
            self.log(f"\n[FAILURE] C Compiler failed. (Exit code {exit_code})")
            self.set_running_state(False)
        self.c_process = None

    def start_step3_run(self, bin_file):
        if not os.path.exists(bin_file):
            self.log(f"\n[ERROR] Step 2 finished, but binary '{os.path.basename(bin_file)}' was not found.")
            self.set_running_state(False)
            return
            
        # Natively execution formatting (./file.out on linux, file.exe on windows)
        exec_path = bin_file if sys.platform == "win32" else f"./{os.path.basename(bin_file)}"
            
        self.log(f"\n[STEP 3] Executing {os.path.basename(bin_file)}...\n---------------------------------------------------------")
        
        self.exec_process = QProcess(self)
        self.exec_process.setWorkingDirectory(os.path.dirname(self.current_compile_path))
        
        self.exec_process.readyReadStandardOutput.connect(lambda: self.log(bytes(self.exec_process.readAllStandardOutput()).decode("utf8", errors="ignore").strip(), new_line=False))
        self.exec_process.readyReadStandardError.connect(lambda: self.log(f"[RUNTIME ERROR] {bytes(self.exec_process.readAllStandardError()).decode('utf8', errors='ignore').strip()}", new_line=False))
        self.exec_process.finished.connect(self.step3_finished)
        
        self.exec_process.start(exec_path)

    def step3_finished(self, exit_code, exit_status):
        self.log(f"\n---------------------------------------------------------\n[FINISHED] Process exited with code {exit_code}")
        self.exec_process = None
        self.current_compile_path = None
        self.set_running_state(False)

    def log(self, text, new_line=True):
        if not text: return
        
        scrollbar = self.console.verticalScrollBar()
        is_at_bottom = scrollbar.value() == scrollbar.maximum()
        
        if new_line:
            self.console.append(text)
        else:
            self.console.moveCursor(QTextCursor.MoveOperation.End)
            self.console.insertPlainText(text + "\n")
            
        if is_at_bottom:
            scrollbar.setValue(scrollbar.maximum())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MadIDE()
    w.show()
    sys.exit(app.exec())
