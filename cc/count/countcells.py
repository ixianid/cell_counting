import numpy as np
import skimage as ski
import os
from matplotlib import pyplot as plt
from skimage.feature import blob_dog, blob_log, blob_doh
from skimage.color import rgb2gray
from math import sqrt

log_defaults = {
    'min_s': 1,
    'max_s': 30,
    'num_s': 10,
    'thresh':0.1,
    'overlap': 0.5,
    'log_scale': False,
    'exclude_border': False
}

def run_log(image, plot_im = False, verbose = False, log_params = log_defaults):
    
    if verbose == True:
        print (log_params)

    # Find blobs with Laplacian of Gaussian
    blobs_log = blob_log(
        image, 
        min_sigma = log_params['min_s'],
        max_sigma = log_params['max_s'], 
        num_sigma = log_params['num_s'], 
        threshold = log_params['thresh'],
        overlap = log_params['overlap'],
        log_scale = log_params['log_scale'],
        exclude_border = log_params['exclude_border']
        )

    if len(blobs_log) == 0:
        print('No Blobs')
    # Compute radii in the 3rd column.
    blobs_log[:, 2] = blobs_log[:, 2] * sqrt(2)
    
    if plot_im == True:
        # Generate figure to check accuracy
        fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(20, 10), sharex=True, sharey=True)
        ax0.imshow(image)
        ax1.imshow(image)
        for blob in blobs_log:
            y, x, r = blob
            c = plt.Circle((x, y), r, color='r', linewidth=2, fill=False)
            ax1.add_patch(c)
        plt.tight_layout()
        plt.show()
        return fig, blobs_log

    # Return fig and blobs_log for counting blobs
    return blobs_log


class cell_counts:
    def __init__(self, name, image, blobs, pixels_per_micron, log_params):
        self.id = os.path.basename(name)[0:5]
        self.name = name 
        self.image = image
        self.blobs = blobs[blobs[:,2] > 2] # restriction on minimum blob size
        self.pixels_per_micron = pixels_per_micron
        self.log_params = log_params
    
    @ property
    def num_cells(self):
        return len(self.blobs)
    
    @ property
    def im_area(self):
        microns_per_pixel = 1/self.pixels_per_micron
        im_area = self.image.shape[0] * self.image.shape[1] * microns_per_pixel**2
        return im_area

    @ property
    def slice_area(self):
        """
        CMH 20191217
            Adding the below to extract only pixels above value
            This is to extract area of the actual slice rather than the
            area of the image, will save a lot of time cropping images  
            
            Sum across RGB pixel values to get one value for boolean
            Update: Passing only green channel so not necessary 
                #sim = np.sum(self.image, axis = 2)

            Calculate number of pixels with value > 1
                Note: 1 is chosen as occasionally black pixels are [0,1,0]
                as well as [0,0,0]

                #

            Return slice area = num true pixels * mpp^2
        """
        bim = self.image[self.image>1]
        microns_per_pixel = 1/self.pixels_per_micron
        slice_area = bim.size * microns_per_pixel**2  
        return slice_area

    @ property
    def cells_per_um2(self):
         um2 = self.slice_area
         cells_per_um2 = self.num_cells/um2
         return cells_per_um2 

    @ property
    def cells_per_mm2(self):
        return self.cells_per_um2 * 1e6

    @ property
    def percent_slice(self):
        return 100 * self.slice_area/self.im_area

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'image': self.image,
            'blobs': self.blobs,
            'pixels_per_micron': self.pixels_per_micron,
            'num_cells': self.num_cells,
            'im_area': self.im_area,
            'slice_area': self.slice_area,
            'cells_per_um2': self.cells_per_um2,
            'cells_per_mm2': self.cells_per_mm2,
            'percent_slice': self.percent_slice,
            'LOG_params': self.log_params
        }

    def overlay(self, return_fig = False):
        fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(20, 10), sharex=True, sharey=True)
        ax0.imshow(self.image)
        ax1.imshow(self.image)
        for blob in self.blobs:
            y, x, r = blob
            c = plt.Circle((x, y), r, color='r', linewidth=2, fill=False)
            ax1.add_patch(c)
        plt.tight_layout()
        plt.show()
        if return_fig == True:
            return fig
        else:
            return


def collect_cell_counts(
    image_directory,  
    log_params = log_defaults,
    testi = 0, 
    verbose = False,
    pixels_per_micron = 1.5
    ): 
    images = ski.io.ImageCollection(os.path.join(image_directory, '*.tif'))
    
    # For testing, allow the check of first set of images up to i = testi
    if testi > 0:
        images = images[0:testi]
        
    # Verbose
    if verbose == True:
        print ('LOG parameters are:')
        print (log_params)
        print()
        print ('The first 5 files are:')
        print (images.files[0:5])
        print ('...')
        print ('The last 5 files are:')
        print (images.files[-5:])
        print()
      
    # Run 
    counted = []
    for i, image in enumerate(images):
        if verbose == True:
            print('i is:', i)
            print("Current file is:")
            print(images.files[i])
            print()     
        
        """
        Commenting out for training
        if verbose == False:
            if i%10 == 0:
                print('Current index:', i) 
        """

        greyscale_im = rgb2gray(image)
        image8 = ski.img_as_ubyte(greyscale_im)
        blobs_log = run_log(image8, plot_im = False, log_params = log_params)
        clob = cell_counts(
                    name = images.files[i], 
                    image = image8, 
                    blobs = blobs_log,
                    pixels_per_micron= pixels_per_micron,
                    log_params = log_params
                    )
        counted.append(clob)

    return counted       

def clob_to_dict(clob):
        return {
            'id': clob.id,
            'name': os.path.basename(clob.name)[:-4],
            #'image': clob.image,
            #'blobs': clob.blobs,
            #'pixels_per_micron': clob.pixels_per_micron,
            'num_cells': clob.num_cells,
            #'im_area': clob.im_area,
            'slice_area': clob.slice_area,
            'cells_per_um2': clob.cells_per_um2,
            'cells_per_mm2': clob.cells_per_mm2,
            'percent_slice': clob.percent_slice  
        }

def extract_panda(clob_list):
    dictlist = []
    for i in range(len(clob_list)):
        dictlist += [clob_to_dict(clob_list[i])]
    DF = pd.DataFrame(dictlist)
    return DF