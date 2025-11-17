import argparse
from xml.dom import minidom
import xml.etree.ElementTree as ET

def args_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=str, help="Source code file (for assemble mode)")
    parser.add_argument("--out", type=str, help="Binary output file (assemble mode)")
    parser.add_argument("--test-mode", action="store_true", help="Run in test mode (assemble mode)")
    parser.add_argument("--interpret", action="store_true", help="Run interpreter on binary file (interpret mode)")
    parser.add_argument("--bin", type=str, help="Binary file to interpret (interpret mode)")
    parser.add_argument("--dump", type=str, help="Output XML dump file (interpret mode)")
    parser.add_argument("--dump-start", type=int, default=0, help="Dump start address (interpret mode)")
    parser.add_argument("--dump-end", type=int, default=255, help="Dump end address (interpret mode)")
    args = parser.parse_args()

    if args.interpret:
        if not args.bin:
            print("Бинарный файл не указан (используйте --bin)")
            exit(1)
        if not args.dump:
            print("Файл дампа не указан (используйте --dump)")
            exit(1)
    else:
        if not args.src:
            print("Файл исходного кода не указан (используйте --src)")
            exit(1)
        if not args.out:
            print("Файл вывода не указан (используйте --out)")
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
        # пропуск строк-комментариев
        if line.startswith('#') or line.startswith('//') or line.startswith(';'):
            continue
        # убираем ; для комментариев в конце строки
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
        # A 0-4, B 5-23 (19), C 24-55 (32) -> 56 -> 7 байт
        B = f.get('B', 0)
        C = f.get('C', 0)
        if B >= (1 << 19) or B < 0:
            raise ValueError('Поле B вне диапазона для ld')
        if C >= (1 << 32) or C < 0:
            raise ValueError('Поле C вне диапазона для ld')
        val = opcode | (B << 5) | (C << 24)
        size = 7

    elif m == 'rd':
        # A 0-4, B 5-23 (19), C 24-42 (19) -> 42 -> 6 байт
        B = f.get('B', 0)
        C = f.get('C', 0)
        if B >= (1 << 19) or B < 0:
            raise ValueError('Поле B вне диапазона для rd')
        if C >= (1 << 19) or C < 0:
            raise ValueError('Поле C вне диапазона для rd')
        val = opcode | (B << 5) | (C << 24)
        size = 6

    elif m == 'wr':
        # A 0-4, B 5-14 (10), C 15-33 (19), D 34-52 (19) -> 53 -> 7 байт
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
        # A 0-4, B 5-23 (19), D 24-42 (19), C 43-61 (19) -> 62 -> 8 байт
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


def decode_instruction_from_bytes(data: bytes, offset: int):
    if offset >= len(data):
        return None, 0
    opcode = data[offset] & 0x1F  # 0-4 
    rev_map = {v: k for k, v in MNEMONICS.items()}
    if opcode not in rev_map:
        raise ValueError(f'Неизвестный код операции {opcode} на смещении {offset}')
    mnemonic = rev_map[opcode]
    size_map = {'ld':7, 'rd':6, 'wr':7, 'bir':8}
    size = size_map[mnemonic]
    if offset + size > len(data):
        raise ValueError('Неожиданный конец кода при декодировании инструкции')
    chunk = int.from_bytes(data[offset:offset+size], byteorder='little', signed=False)

    # извлечение полей по позициям битов, соответствующих кодированию
    if mnemonic == 'ld':
        B = (chunk >> 5) & ((1 << 19) - 1)
        C = (chunk >> 24) & ((1 << 32) - 1)
        fields = {'B': B, 'C': C}
    elif mnemonic == 'rd':
        B = (chunk >> 5) & ((1 << 19) - 1)
        C = (chunk >> 24) & ((1 << 19) - 1)
        fields = {'B': B, 'C': C}
    elif mnemonic == 'wr':
        B = (chunk >> 5) & ((1 << 10) - 1)
        C = (chunk >> 15) & ((1 << 19) - 1)
        D = (chunk >> 34) & ((1 << 19) - 1)
        fields = {'B': B, 'C': C, 'D': D}
    elif mnemonic == 'bir':
        B = (chunk >> 5) & ((1 << 19) - 1)
        D = (chunk >> 24) & ((1 << 19) - 1)
        C = (chunk >> 43) & ((1 << 19) - 1)
        fields = {'B': B, 'C': C, 'D': D}
    else:
        fields = {}

    instr = {'mnemonic': mnemonic, 'opcode': opcode, 'fields': fields, 'size': size}
    return instr, size


def rotate_right(value: int, shift: int, width: int = 64) -> int:
    shift %= width
    mask = (1 << width) - 1
    return ((value >> shift) | ((value << (width - shift)) & mask)) & mask


def run_interpreter(code_bytes: bytes, dump_start: int, dump_end: int):
    code_mem = code_bytes
    data_mem = {}  # адрес -> целое число

    ip = 0
    while ip < len(code_mem):
        instr, size = decode_instruction_from_bytes(code_mem, ip)
        if instr is None:
            break
        m = instr['mnemonic']
        f = instr['fields']

        if m == 'ld':
            B = f['B']; C = f['C']
            data_mem[B] = C
        elif m == 'rd':
            B = f['B']; C = f['C']
            data_mem[C] = data_mem.get(B, 0)
        elif m == 'wr':
            B = f['B']; C = f['C']; D = f['D']
            addr = data_mem.get(D, 0) + B
            data_mem[addr] = data_mem.get(C, 0)
        elif m == 'bir':
            B = f['B']; C = f['C']; D = f['D']
            a = data_mem.get(C, 0)
            b = data_mem.get(B, 0)
            data_mem[D] = rotate_right(a, b, 64)

        ip += size

    # сборка дампа в XML
    root = ET.Element('memory')
    for addr in range(dump_start, dump_end + 1):
        cell = ET.SubElement(root, 'cell')
        cell.set('address', str(addr))
        cell.text = str(data_mem.get(addr, 0))

    return ET.ElementTree(root)


def write_pretty_xml(tree: 'ET.ElementTree', path: str):
    # produce indented, human-readable XML using minidom
    root = tree.getroot()
    rough = ET.tostring(root, 'utf-8')
    reparsed = minidom.parseString(rough)
    pretty = reparsed.toprettyxml(indent="  ")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(pretty)

if __name__ == "__main__":
    args = args_parser()

    if args.interpret:
        # Режим интерпретации: чтение бинарного файла, запуск интерпретатора, запись дампа в XML
        with open(args.bin, 'rb') as f:
            code = f.read()

        tree = run_interpreter(code, args.dump_start, args.dump_end)
        write_pretty_xml(tree, args.dump)
        print(f"Дамп записан в: {args.dump}")
    else:
        # Режим сборки
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
