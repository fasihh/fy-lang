import argparse
import os
import sys
from src.tokenizer import tokenize
from src.parser import Parser
from src.interpreter import Interpreter
from version import __version__


def no_traceback_hook(exc_type, exc_value, _exc_traceback):
    print("", f"{exc_type.__name__}: {exc_value}\n", sep="\n")


sys.excepthook = no_traceback_hook

KEY = b"fylang"


def compile_to_binary(ast, output_file):
    import pickle

    with open(output_file, "wb") as f:
        f.write(KEY)
        pickle.dump(ast, f)


def load_binary(file_path):
    import pickle

    with open(file_path, "rb") as f:
        magic = f.read(len(KEY))
        if magic != KEY:
            raise RuntimeError("Invalid binary format")
        return pickle.load(f)


def interpret_source(file_path, generate_binary=False):
    with open(file_path, "r") as f:
        code = f.read()

    tokens = tokenize(code)
    parser = Parser(tokens)
    ast = parser.parse()

    if generate_binary:
        output_file = os.path.splitext(file_path)[0] + ".fy.b"
        compile_to_binary(ast, output_file)
        return

    interpreter = Interpreter()
    interpreter.interpret(ast)


def interpret_binary(file_path):
    ast = load_binary(file_path)
    interpreter = Interpreter()
    interpreter.interpret(ast)


def main():
    parser = argparse.ArgumentParser(description="fylang CLI")
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument("file", help="Source file (.fy) or binary file (.fy.b)")
    parser.add_argument(
        "-b",
        "--binary",
        action="store_true",
        help="Compile to binary instead of interpreting",
    )
    parser.add_argument(
        "-t",
        "--traceback",
        action="store_true",
        help="Enable full Python exception tracebacks",
    )

    args = parser.parse_args()

    if args.traceback:
        sys.excepthook = sys.__excepthook__

    if args.file.endswith(".fy.b"):
        interpret_binary(args.file)
    else:
        interpret_source(args.file, generate_binary=args.binary)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
