import argparse
import json

def args_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=str, help="Source code file")
    parser.add_argument("--out", type=str, help="Binary output file")
    parser.add_argument("--test-mode", action="store_true", help="Run in test mode")
    args = parser.parse_args()

    if not args.src:
        print("Файл исходного кода не указан")
        exit(1)
    elif not args.out:
        print("Файл вывода не указан")
        exit(1)
    
    return args


MNEMONICS = {
    'ld':  1,
    'rd':  2,
    'wr':  3,
    'bir': 4,
}


def parse_operand_list(ops_text: str):
    # ops_text - например '12, 142' или '2, 12, 14'
    parts = [p.strip() for p in ops_text.split(',') if p.strip()]
    vals = []
    for p in parts:
        # пока только целые числа
        try:
            v = int(p)
        except ValueError:
            raise ValueError(f"Неверное значение операнда: '{p}'")
        vals.append(v)
    return vals


def parse_assembly(text: str):
    lines = text.splitlines()
    program = []
    for lineno, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line:
            continue
        # убираем ; для комментариев и другого в конце
        if ';' in line:
            line = line[:line.rfind(';')].strip()
        if not line:
            continue

        # разделение мнемоники и операндов
        parts = line.split(None, 1)
        if len(parts) == 0:
            continue
        mnemonic = parts[0].lower()
        ops_text = parts[1] if len(parts) > 1 else ''

        if mnemonic not in MNEMONICS:
            raise ValueError(f"Неизвестная мнемоника '{mnemonic}' на строке {lineno}")

        operands = []
        if ops_text:
            operands = parse_operand_list(ops_text)

        # сопоставление операндов с именованными полями согласно общей форме спецификации УВМ
        # используем имена полей B, C, D по порядку (до 3 операндов)
        field_names = ['B', 'C', 'D']
        fields = {}
        for i, val in enumerate(operands):
            if i < len(field_names):
                fields[field_names[i]] = val
            else:
                # для простоты разрешаем дополнительные числовые поля как F1,F2...
                fields[f'F{i+1}'] = val

        instr = {
            'mnemonic': mnemonic,
            'opcode': MNEMONICS[mnemonic],
            'fields': fields,
        }
        program.append(instr)

    return program


def print_internal_representation(program):
    # Печать каждой инструкции как полей и значений, аналогично формату теста УВМ
    for idx, instr in enumerate(program):
        print(f"Инструкция {idx}:")
        print(f"  мнемоника: {instr['mnemonic']}")
        print(f"  код операции: {instr['opcode']}")
        # Печать B,C,D затем любые другие
        order = ['B', 'C', 'D'] + sorted([k for k in instr['fields'].keys() if k not in ('B','C','D')])
        for k in order:
            if k in instr['fields']:
                print(f"  {k}: {instr['fields'][k]}")
        print()

if __name__ == "__main__":
    args = args_parser()

    with open(args.src, 'r', encoding='utf-8') as f:
        src = f.read()

    program = parse_assembly(src)

    if args.test_mode:
        print_internal_representation(program)
    else:
        if args.out:
            with open(args.out, 'w', encoding='utf-8') as f:
                json.dump(program, f, indent=2)
        else:
            print("Программа не в тестовом режиме. Используйте --test-mode для печати внутреннего представления.")
