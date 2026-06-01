# MAD IDE

![MAD IDE](https://madide.vercel.app/assets/hero.png)

🌐 **Official Website & Downloads:** [https://madide.vercel.app/](https://madide.vercel.app/)

MAD IDE is a modern, native graphical editor and compiler pipeline for the **Michigan Algorithm Decoder (MAD)** language—a highly influential algebraic programming language developed in 1959. This IDE allows you to write, edit, and execute original historical MAD programs (such as the original ELIZA chatbot) directly on modern hardware!

## Features

- **Modern UI:** Built with PyQt6, featuring a gorgeous dark mode and light mode, a file explorer, and a tabbed editor.
- **Intelligent Preprocessing:** The IDE automatically handles historical IBM 7090 line-padding (columns 6 to 11) so you can write freely without spacing errors.
- **CTSS Abbreviations:** Automatically expands early Compatible Time-Sharing System (CTSS) shorthands (e.g., expanding `W'R` to `WHENEVER` and `E'L` to `END OF CONDITIONAL`).
- **One-Click Native Execution:** The built-in pipeline transpiles your MAD code to C and natively compiles it using `gcc`/`clang` in the background. Just press `F5`!
- **Custom Syntax Highlighting:** Integrated QScintilla lexer exclusively tailored for MAD's unique syntax and string literals (`$`).

## Prerequisites

To use the transpilation pipeline, your system must have the following installed:
- `make`
- A C Compiler (`gcc` or `clang`)
- Python 3.x

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ahmadshajhan/madide.git
   cd madide
   ```

2. **Install Python dependencies:**
   ```bash
   pip install PyQt6 PyQt6-QScintilla ply
   ```

3. **Run the IDE:**
   ```bash
   python main.py
   ```

## Getting Started

1. When you open the IDE, you must first build the underlying MAD transpiler. Go to **Tools -> Build MAD Compiler** in the top menu.
2. Open a `.mad` file (such as `hello.mad` or `eliza.mad`) from the built-in file explorer.
3. Click the **▶ Run** button or press **F5**.
4. Interact with your compiled program directly through the embedded output console!

---

*For detailed documentation and original code examples, please visit [madide.vercel.app/docs.html](https://madide.vercel.app/docs.html).*
