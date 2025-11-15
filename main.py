import argparse

def args_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=str, help="Source code file")
    parser.add_argument("--out", type=str, help="Binary output file")
    parser.add_argument("--test-mode", action="store_true", help="Run in test mode")
    args = parser.parse_args()

    if not args.src:
        print("Source file not set")
        exit(1)
    elif args.out:
        print("Output file not set")
        exit(1)
    
    return args

if __name__ == "__main__":
    args_parser()
