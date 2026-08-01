import cv2
import numpy as np
'''
切割匹配
mask遮罩
'''

def show_resulte():
    map_path = 'map.png'
    char_template_path = 'img/nametag/example.png'
    mask_path = 'img/nametag/example.png'

    img_source = cv2.imread(map_path)
    img_source_gray = cv2.cvtColor(img_source, cv2.COLOR_BGR2GRAY) 
    img_char_template = cv2.imread(char_template_path, cv2.IMREAD_GRAYSCALE)
    img_mask = cv2.imread(mask_path, cv2.IMREAD_COLOR)

    h, w = img_char_template.shape[:2]
    print(f"模板圖片尺寸: 高度={h}, 寬度={w}")
    SPITE_WIDTH = 40
    num_splits = max(1, w // SPITE_WIDTH)
    w_splits = w // num_splits
    print(f"將模板圖片分割為 {num_splits} 個區塊，每個區塊寬度為 {SPITE_WIDTH} 像素。")

    #遮罩

    mask = get_mask(img_mask, ignore_pixel_color=(0, 255, 0))

    matches = []
    #split the template into multiple parts
    for i in range(num_splits):
        x_start = i * w_splits  
        x_end = (i+1) * w_splits if i < num_splits - 1 else w 

        slpit_template = img_char_template[:, x_start:x_end]
        split_mask = mask[:, x_start:x_end] 

        result = cv2.matchTemplate(
            img_source_gray, slpit_template , cv2.TM_SQDIFF_NORMED, mask=split_mask
        )
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        # min_loc 是這一份切片「自己」在地圖上找到的最佳匹配左上角座標
        loc = min_loc
        score = min_val

        matches.append({
            "tag_type": f"{i+1}/{num_splits}",
            "loc": loc,
            "score": score,
            "w": slpit_template.shape[1],
            "h": slpit_template.shape[0],
            "offset_x": x_start,
        })

        print(f"  區塊 {i+1}/{num_splits}: 找到位置={loc}, "
            f"分數(越小越準)={score:.4f}")

        # 選出分數最好(最小)的那個區塊
    best = min(matches, key=lambda m: m["score"])
    print(f"\n最佳匹配區塊: {best['tag_type']}, 分數={best['score']:.4f}")

    # 把「這個區塊找到的位置」換算回「整個名牌」的位置
    # 因為找到的是這個切片的左上角，要扣掉這個切片的 offset_x 才能回推整個名牌的左上角
    nametag_x = best["loc"][0] - best["offset_x"]
    nametag_y = best["loc"][1]
    print(f"換算回整個名牌的左上角座標: ({nametag_x}, {nametag_y})")

    # 在地圖上畫出每個切片各自找到的位置 (細框，方便比較)，
    # 以及換算回來的完整名牌框 (粗框，最終結果)
    img_debug = img_source.copy()


    cv2.rectangle(img_debug, (nametag_x, nametag_y),
                  (nametag_x + w, nametag_y + h), (0, 255, 0), 2)
    cv2.putText(img_debug, "FINAL", (nametag_x, nametag_y + h + 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    cv2.imwrite("result.png", img_debug)

    cv2.imshow("Map", img_debug)
    cv2.imshow("name_tag", split_mask)

    cv2.waitKey(0)
    cv2.destroyAllWindows()


def get_mask(img, ignore_pixel_color):
    '''
    產生前景遮罩:指定顏色的像素會被忽略
    '''
    mask = np.all(img == ignore_pixel_color, axis=2).astype(np.uint8) * 255
    mask = cv2.bitwise_not(mask)
    return mask

if __name__ == "__main__":
    show_resulte()