

# import zbar
# import cv2
# import psycopg2
#
#
# def load_image(infilename):
#
#     im = cv2.imread(infilename, 0)
#     print(type(im))
#     return im
#
#
# def get_barcode_details(barcode):
#     barcode_det = ()
#     try:
#         conn = psycopg2.connect("dbname=barcode user=barcode_user password=shroot12")
#         cur = conn.cursor()
#         cur.execute('select * from barcode_details where barcode_id={}'.format(barcode))
#         barcode_det = cur.fetchone()
#     except (Exception, psycopg2.DatabaseError) as error:
#         print(error)
#     finally:
#         cur.close()
#     return barcode_det
#
# barcode = None
# barcode_details = ()
# image = load_image('/home/sreeram/Downloads/barcode.png')
# # whatever function you use to read an image file into a numpy array
# scanner = zbar.Scanner()
# results = scanner.scan(image)
#
# for result in results:
#     barcode = result.data.decode('ascii')
#
# if barcode:
#     barcode_details = get_barcode_details(barcode)
#     store_data = {barcode_details[0]: (barcode_details[1], barcode_details[2], barcode_details[3])}
#     print(store_data)
#
#     print('|'.join(sorted(
#         [','.join([str(idd), str(product_name), str(mfg_date), location]) for idd, (product_name, mfg_date, location) in
#          store_data.items()])).encode())
    # print('|'.join(sorted(
    #     [','.join([idd, product_name, mfg_date, location]) for idd, (product_name, mfg_date, location) in
    #      store_data.items()])))






#
# import zbar.misc
# import zbar
#
# import time
# import pygame
# import pygame.camera
# import pygame.image
# import pygame.surfarray
#
#
# def get_image_array_from_cam(cam_name, cam_resolution):
#     '''Get animage ndarray from webcam using pygame.'''
#     pygame.init()
#     pygame.camera.init()
#     pygame.camera.list_cameras()
#     cam = pygame.camera.Camera(cam_name, cam_resolution)
#
#     screen = pygame.display.set_mode(cam.get_size())
#     print('Get a pic of barcode. If pic doesnot look good, then press enter at terminal. \
#            Camera will take another pic. When done press q and enter to quit camera mode')
#     while True:
#         cam.start()
#         time.sleep(0.5)  # You might need something higher in the beginning
#         pygame_screen_image = cam.get_image()
#         screen.blit(pygame_screen_image, (0,0))
#         pygame.display.flip() # update the display
#         cam.stop()
#         if input() == '1':
#             break
#
#     pygame.display.quit()
#
#     image_ndarray = pygame.surfarray.array3d(pygame_screen_image)
#
#     if len(image_ndarray.shape) == 3:
#         image_ndarray = zbar.misc.rgb2gray(image_ndarray)
#
#     return image_ndarray
#
#
# #----------------------------------------------------------------------------------
# # Get the pic
# # To get pic from cam or video, packages like opencv or simplecv can also be used.
# #----------------------------------------------------------------------------------
#
# # Cam name might vary depending on your PC.
# cam_name = '/dev/video0'
# cam_resolution = (640, 480)      # A general cam resolution
#
# img_ndarray = get_image_array_from_cam(cam_name, cam_resolution)
#
# #-------------------------------------------------------------------------
# # Read the Barcode
# #-------------------------------------------------------------------------
#
# # Detect all
# scanner = zbar.Scanner()
# results = scanner.scan(img_ndarray)
#
# if results == []:
#     print("No Barcode found.")
# else:
#     for result in results:
#         # By default zbar returns barcode data as byte array, so decode byte array as ascii
#         print(result.data.decode("ascii"))


import zbar.misc
import zbar
import time
import pygame
import pygame.camera
import pygame.image
import pygame.surfarray


class BarcodeReader(object):

    def __init__(self):
        self.cam_name = '/dev/video0'
        self.cam_resolution = (640, 480)  # A general cam resolution
        self.scanner = zbar.Scanner()

    def get_image_array_from_cam(self):
        pygame.init()
        pygame.camera.init()
        pygame.camera.list_cameras()
        cam = pygame.camera.Camera(self.cam_name, self.cam_resolution)

        screen = pygame.display.set_mode(cam.get_size())
        print('Get a pic of barcode. If pic doesnot look good, then press enter at terminal. \n\
           Camera will take another pic. When done press q and enter to quit camera mode')
        while True:
            cam.start()
            time.sleep(0.5)  # You might need something higher in the beginning
            pygame_screen_image = cam.get_image()
            screen.blit(pygame_screen_image, (0,0))
            pygame.display.flip() # update the display
            cam.stop()
            if input() == 'q':
                break

        pygame.display.quit()
        image_ndarray = pygame.surfarray.array3d(pygame_screen_image)
        if len(image_ndarray.shape) == 3:
            image_ndarray = zbar.misc.rgb2gray(image_ndarray)

        return image_ndarray

    def read_barcode_by_cam(self):
        img_array = self.get_image_array_from_cam()
        results = self.scanner.scan(img_array)
        if results == []:
            return None
        else:
            for result in results:
                return result.data.decode("ascii")




