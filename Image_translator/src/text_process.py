# -*- coding: gbk -*-
from PIL import Image, ImageDraw, ImageFont  # ����ͼƬ�����滻
from pathlib import Path


def merge_text_lines(ocr_results, max_line_gap=1, max_x_diff=1):
    # ����λ����Ϣ�ϲ�����ͬһ���ӵ��ı���
    # :param ocr_results: OCRʶ�����б�
    # :param max_line_gap: ����м�ࣨ������иߵı�����
    # :param max_x_diff: ���ˮƽƫ�ƣ�������п�ı�����
    # :return: �ϲ�����ı������б�

    if not ocr_results:
        return []

    # ����
    sorted_results = sorted(ocr_results, key=lambda x: (x['location']['top'], x['location']['left']))
    paragraphs = []

    for res in sorted_results:
        loc = res['location']
        top, left, height, width = loc['top'], loc['left'], loc['height'], loc['width']

        flag = True
        for para in paragraphs:
            if not para:
                continue
            last_bottom = para['res'][-1]['location']['top'] + para['res'][-1]['location']['height']
            last_left = para['res'][-1]['location']['left']
            if (top - last_bottom) <= height * max_line_gap and abs(left - last_left) <= max_x_diff:
                para['res'].append(res)
                flag = False
                break

        if flag:
            paragraphs.append({'res': [res]})

    for para in paragraphs:
        words = ""
        for res in para['res']:
            words += res['words'] + '\n'
        para['words'] = words

    return paragraphs


def replace_text_in_image(original_path, output_path, paragraphs, translations):
    # ��ͼƬ���滻����
    try:
        # ��ԭʼͼƬ
        img = Image.open(original_path)
        draw = ImageDraw.Draw(img)

        # ���Լ����������壬���ʧ����ʹ��Ĭ������
        try:
            # ���Գ�����������·��
            font_paths = [
                "C:/Windows/Fonts/simhei.ttf",  # Windows
                "/System/Library/Fonts/PingFang.ttc",  # macOS
                "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"  # Linux
            ]

            font = None
            for path in font_paths:
                if Path(path).exists():
                    font = ImageFont.truetype(path, 20)  # ��ʼ��С�����������
                    break

            if font is None:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()

        # ����ÿ������
        for i, para1 in enumerate(paragraphs):
            para = para1['res']
            # ������������ı߽�
            left = min(r['location']['left'] for r in para)
            top = min(r['location']['top'] for r in para)
            right = max(r['location']['left'] + r['location']['width'] for r in para)
            bottom = max(r['location']['top'] + r['location']['height'] for r in para)
            width = right - left
            height = bottom - top

            # �����ϲ����λ����Ϣ
            merged_location = {
                'left': left,
                'top': top,
                'width': width,
                'height': height
            }

            # ���Ʊ�������ԭʼ�ı�
            draw.rectangle(
                [(left, top), (right, bottom)],
                fill="white"
            )

            # ���Ʒ������ı�
            text = translations[i]
            font_size = max(10, int(para[0]['location']['height'] * 0.8))

            # ���������С
            if hasattr(font, "path"):  # �����truetype����
                try:
                    font = ImageFont.truetype(font.path, font_size)
                except:
                    pass

            # ���������֣����У�
            # text_width = font.getlength(text) if hasattr(font, "getlength") else len(text) * font_size // 2
            # x = merged_location["left"] + (merged_location["width"] - text_width) // 2
            # y = merged_location["top"] + (merged_location["height"] - font_size) // 2
            x = merged_location["left"]
            y = merged_location["top"]

            draw.text((x, y), text, fill="black", font=font)

        # ������
        img.save(output_path)
        return True
    except Exception as e:
        print(f"ͼƬ�������: {str(e)}")
        return False
