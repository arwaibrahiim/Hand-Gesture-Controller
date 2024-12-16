import numpy as np
import cv2
import math

class adv_hand_detector:

    ###################################### INITIALIZATION #######################################
    def __init__(self, roi_position: str = 'left') -> None:
        '''
        Creates an object of hand_detector, a class that contains all needed functions, variables and tuning variables
        to detect a hand inside ROI
        ----------
        Parameters
        ----------
        roi_position: str
            Position of the ROI block, left or right only
        '''
        if roi_position.lower() == 'left':
            self.x1, self.x2, self.y1, self.y2 = 50, 250, 50, 250
        elif roi_position.lower() == 'right':
            self.x1, self.x2, self.y1, self.y2 = 50, 250, 400, 600
        else:
            raise ValueError('roi_position must be left or right only')
        # Initalize GUI (This part might be removed)
        cv2.namedWindow('Hand Detection')

    def detect(self, frame: np.ndarray) -> None:
        '''
        main function to call to start the detection of the 2 finger process
        ----------
        Parameters
        ----------
        frame: numpy array
            The frame to process
        '''
        roi = frame[self.x1:self.x2, self.y1:self.y2]
        cv2.rectangle(frame, (self.y1, self.x1), (self.y2, self.x2), (0, 255, 0), 0)
        
        mask = self.segment_hand(roi)
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        try:
            cnt = max(contours, key=lambda x: cv2.contourArea(x))
            l = self.analyse_defects(cnt, roi)
            self.analyse_contours(frame, cnt, l + 1)
        except ValueError:
            pass
        self.show_results(mask, frame)

    def segment_hand(self, ROI) -> np.ndarray:

        sobh = cv2.cvtColor(ROI, cv2.COLOR_BGR2RGB)

        # Reshaping the image into a 2D array of pixels and 3 color values (RGB)
        pixel_vals = sobh.reshape((-1,3))

        # Convert to float type
        pixel_vals = np.float32(pixel_vals)

        #the below line of code defines the criteria for the algorithm to stop running, 
        #which will happen is 100 iterations are run or the epsilon (which is the required accuracy) 
        #becomes 85%
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.85)

        # then perform k-means clustering with number of clusters defined as 3
        #also random centres are initially choosed for k-means clustering
        k = 2
        _, labels, centers = cv2.kmeans(pixel_vals, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

        # convert data into 8-bit values
        centers = np.uint8(centers)
        segmented_data = centers[labels.flatten()]

        # reshape data into the original image dimensions
        segmented_image = segmented_data.reshape((sobh.shape))
        segmented_image = cv2.cvtColor(segmented_image, cv2.COLOR_RGB2GRAY)

        masker = (segmented_image < 150) & (segmented_image > 0)
        segmented_image[masker] = 255
        segmented_image[~masker] = 0

        return segmented_image
    
    def analyse_defects(self, cnt, roi: np.ndarray) -> int:
        """
        Calculates how many convexity defects are on the image.
        A convexity defect is a area that is inside the convexity hull but does not belong to the object.
        Those defects in our case represent the division between fingers.
        ----------
        Parameters
        ----------
        cnt : array-like
          Contour of max area on the image, in this case, the contour of the hand

        roi : array-like
          Region of interest where should be drawn the found convexity defects
        """
        epsilon = 0.0005 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)

        hull = cv2.convexHull(approx, returnPoints=False)
        defects = cv2.convexityDefects(approx, hull)

        l = 0
        if defects is not None:
            for i in range(defects.shape[0]):
                s, e, f, d = defects[i, 0]
                start = tuple(approx[s][0])
                end = tuple(approx[e][0])
                far = tuple(approx[f][0])

                a = math.sqrt((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2)
                b = math.sqrt((far[0] - start[0]) ** 2 + (far[1] - start[1]) ** 2)
                c = math.sqrt((end[0] - far[0]) ** 2 + (end[1] - far[1]) ** 2)
                s = (a + b + c) / 2
                ar = math.sqrt(s * (s - a) * (s - b) * (s - c))
                d = (2 * ar) / a
                angle = math.acos((b ** 2 + c ** 2 - a ** 2) / (2 * b * c)) * 57

                if angle <= 90 and d > 30:
                    l += 1
                    cv2.circle(roi, far, 3, [255, 0, 0], -1)
                cv2.line(roi, start, end, [0, 255, 0], 2)
        return l

    def analyse_contours(self, frame: np.ndarray, cnt, l: int) -> None:
        """
        Writes to the image the signal of the hand.
        The hand signals can be the numbers from 0 to 5, the 'ok' signal, and the 'all right' symbol.
        The signals is first sorted by the number of convexity defects. Then, if the number of convexity defects is 1, 2, or 3, the area ratio is to be analysed.
        Parameters
        ----------
        frame : array-like
          The frame to be analysed
        cnt : array-like
          Contour of max area on the image, in this case, the contour of the hand
        l : int
          Number of convexity defects
        """
        hull = cv2.convexHull(cnt)

        areahull = cv2.contourArea(hull)
        areacnt = cv2.contourArea(cnt)

        arearatio = ((areahull - areacnt) / areacnt) * 100

        font = cv2.FONT_HERSHEY_SIMPLEX
        if l == 1:
            if areacnt < 2000:
                cv2.putText(frame, 'Put hand in the box', (0, 50), font, 2, (0, 0, 255), 3, cv2.LINE_AA)
            else:
                if arearatio < 12:
                    cv2.putText(frame, '0', (0, 50), font, 2, (0, 0, 255), 3, cv2.LINE_AA)
                elif arearatio < 17.5:
                    cv2.putText(frame, 'Fixe', (0, 50), font, 2, (0, 0, 255), 3, cv2.LINE_AA)
                else:
                    cv2.putText(frame, '1', (0, 50), font, 2, (0, 0, 255), 3, cv2.LINE_AA)
        elif l == 2:
            cv2.putText(frame, '2', (0, 50), font, 2, (0, 0, 255), 3, cv2.LINE_AA)
        elif l == 3:
            if arearatio < 27:
                cv2.putText(frame, '3', (0, 50), font, 2, (0, 0, 255), 3, cv2.LINE_AA)
            else:
                cv2.putText(frame, 'ok', (0, 50), font, 2, (0, 0, 255), 3, cv2.LINE_AA)
        elif l == 4:
            cv2.putText(frame, '4', (0, 50), font, 2, (0, 0, 255), 3, cv2.LINE_AA)
        elif l == 5:
            cv2.putText(frame, '5', (0, 50), font, 2, (0, 0, 255), 3, cv2.LINE_AA)
        elif l == 6:
            cv2.putText(frame, 'reposition', (0, 50), font, 2, (0, 0, 255), 3, cv2.LINE_AA)
        else:
            cv2.putText(frame, 'reposition', (10, 50), font, 2, (0, 0, 255), 3, cv2.LINE_AA)

    def show_results(self, mask: np.ndarray, frame: np.ndarray) -> None:
        """
        Shows the image with the results on it.
        The image is a result of a combination of the image with the result on it, the original captured ROI, and the ROI after optimizations.
        ----------
        Parameters
        ----------
        binary_mask : array-like
          ROI as it is captured

        mask : array-like
          ROI after optimizations

        frame : array-like
          Frame to be displayed
        """
        height, _, _ = frame.shape
        _, width = mask.shape
        masks_result = cv2.resize(mask, dsize=(width, height))
        masks_result = cv2.cvtColor(masks_result, cv2.COLOR_GRAY2BGR)
        result_image = np.concatenate((frame, masks_result), axis=1)
        cv2.imshow('Hand Detection', result_image)