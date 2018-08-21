from PIL import Image

def rotateCrop(imgPath, length, output=None):
    img = Image.open(imgPath)
    width, height = img.size
    if height > width:
        # Perform the counter clockwise rotation holding at the center
        # 90 degrees CW = 270 CCW
        img = img.rotate(270)
    # Expected: 5184 x 3456
    Left = (width-length)//2
    Upper = (height-length)//2
    Right = (width+length)//2
    Lower = (height+length)//2
    crop_img = img.crop((Left, Upper, Right, Lower))
    #crop_img.show()
    if output != None:
        crop_img.save(output)
    else:
        return crop_img