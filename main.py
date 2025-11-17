import argparse

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


def encode_instruction(instr):
    m = instr['mnemonic']
    f = instr['fields']
    opcode = instr['opcode'] & 0x1F  # 0-4 bits

    if m == 'ld':
        # A bits 0-4, B bits 5-23 (19), C bits 24-55 (32) -> 56 bits -> 7 bytes
        B = f.get('B', 0)
        C = f.get('C', 0)
        if B >= (1 << 19) or B < 0:
            raise ValueError('Поле B вне диапазона для ld')
        if C >= (1 << 32) or C < 0:
            raise ValueError('Поле C вне диапазона для ld')
        val = opcode | (B << 5) | (C << 24)
        size = 7

    elif m == 'rd':
        # A 0-4, B 5-23 (19), C 24-42 (19) -> up to bit 42 -> 6 bytes
        B = f.get('B', 0)
        C = f.get('C', 0)
        if B >= (1 << 19) or B < 0:
            raise ValueError('Поле B вне диапазона для rd')
        if C >= (1 << 19) or C < 0:
            raise ValueError('Поле C вне диапазона для rd')
        val = opcode | (B << 5) | (C << 24)
        size = 6

    elif m == 'wr':
        # A 0-4, B 5-14 (10), C 15-33 (19), D 34-52 (19) -> 53 bits -> 7 bytes
        B = f.get('B', 0)
        C = f.get('C', 0)
        D = f.get('D', 0)
        if B >= (1 << 10) or B < 0:
            raise ValueError('Поле B вне диапазона для wr')
        if C >= (1 << 19) or C < 0:
            raise ValueError('Поле C вне диапазона для wr')
        if D >= (1 << 19) or D < 0:
            raise ValueError('Поле D вне диапазона для wr')
        val = opcode | (B << 5) | (C << 15) | (D << 34)
        size = 7

    elif m == 'bir':
        # A 0-4, B 5-23 (19), D 24-42 (19), C 43-61 (19) -> 62 bits -> 8 bytes
        B = f.get('B', 0)
        D = f.get('D', 0)
        C = f.get('C', 0)
        if B >= (1 << 19) or B < 0:
            raise ValueError('Поле B вне диапазона для bir')
        if D >= (1 << 19) or D < 0:
            raise ValueError('Поле D вне диапазона для bir')
        if C >= (1 << 19) or C < 0:
            raise ValueError('Поле C вне диапазона для bir')
        val = opcode | (B << 5) | (D << 24) | (C << 43)
        size = 8

    else:
        raise ValueError(f'Неизвестная мнемоника для кодирования: {m}')

    return val.to_bytes(size, byteorder='little', signed=False)


def assemble_to_bytes(program):
    out = bytearray()
    for instr in program:
        b = encode_instruction(instr)
        out.extend(b)
    return bytes(out)

if __name__ == "__main__":
    args = args_parser()

    with open(args.src, 'r', encoding='utf-8') as f:
        src = f.read()

    program = parse_assembly(src)

    # Собираем в двоичный формат и записываем в выходной файл
    binary = assemble_to_bytes(program)
    with open(args.out, 'wb') as f:
        f.write(binary)

    print(f"Размер бинарного файла: {len(binary)} байт")

    if args.test_mode:
        # Печать внутреннего представления и байтового формата для тестирования
        print_internal_representation(program)
        # Печать байтов в шестнадцатеричном виде, пробел-разделённо
        hex_bytes = ' '.join(f"{b:02X}" for b in binary)
        print("Байтовый формат:")
        print(hex_bytes)
