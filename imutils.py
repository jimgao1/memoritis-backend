
import cv2

def write_first_frame(filename, out_filename):
    cap = cv2.VideoCapture(filename)

    ret, frame = cap.read()
    cv2.imwrite(out_filename, frame)
    cap.release()
