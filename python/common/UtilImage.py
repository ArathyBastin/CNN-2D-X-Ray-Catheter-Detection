from __future__ import division
import os
import sys
import array
import struct
import io
import math
import numpy as np
import colorsys
import pydicom
from pydicom.dataset import Dataset, FileDataset
import pydicom.uid
import skimage as ski
import skimage.io
import skimage.transform
import skimage.draw
import skimage.morphology
import warnings

from Util import *

NORMALIZE_NO = 0
NORMALIZE_SIMPLE = 1
NORMALIZE_CONTRAST_STRETCHING = 2
# NORMALIZE_ADAPTATIVE_EQUALIZATION = 3

def GetFloat32NormalizedFrame(_image, _pixelSize, _normalize = NORMALIZE_NO):
	if _pixelSize == 8:
		maxValue = 255
	elif _pixelSize == 16:
		maxValue = 65535
	elif _pixelSize == 10:
		maxValue = 1023
	else:
		print("GetFloat32NormalizedFrame():: WARNING NOT IMPLEMENTED _pixelSize = " + str(_pixelSize))
		
	_image = _image.astype(np.float32)
	if _normalize == NORMALIZE_SIMPLE:
		min = np.min(_image)
		max = np.max(_image)
		return (_image - min)/(max - min)
	elif _normalize == NORMALIZE_CONTRAST_STRETCHING:
		p2, p98 = np.percentile(_image, (2, 98))
		return ski.exposure.rescale_intensity(_image, in_range=(p2, p98), out_range=(0,1))
	# elif _normalize == NORMALIZE_ADAPTATIVE_EQUALIZATION
		# return ski.exposure.equalize_adapthist(_image, clip_limit=0.03):

	return _image/maxValue

def ReadOnlyDicomInfo(_filename):
	dcmInfo = pydicom.read_file(_filename, stop_before_pixels = True, defer_size = 16)
	# print(dcmInfo.Columns)
	# print(dcmInfo.Rows)
	# print(dcmInfo.NumberOfFrames)
	# print(dcmInfo.BitsStored)
	return dcmInfo
	
def ReadDicomFrame(_filename, _frameId):
	# print(_filename + " " + str(_frameId))
	file = open(_filename, "rb") # TODO use OpenFile here?
	dcmInfo = pydicom.read_file(file, stop_before_pixels = True, defer_size = 16)
	if _frameId < 0 and _frameId >= dcmInfo.NumberOfFrames:
		print("ReadDicomFrame():: ERROR _frameId should be inferior dcmInfo.NumberOfFrames")
		
	# print(dcmInfo.BitsStored)
	if dcmInfo.BitsStored == 16 or dcmInfo.BitsStored == 10:
		pixelType = "H"
		pixelSize = 2 # dcmInfo.BitsStored//8
	elif dcmInfo.BitsStored == 8:
		pixelType = "B"
		pixelSize = 1
	else:
		print("ReadDicomFrame():: WARNING NOT IMPLEMENTED dcmInfo.BitsStored = " + str(dcmInfo.BitsStored))
		
	sizeImageInByte = dcmInfo.Columns*dcmInfo.Rows*pixelSize
	# print(sizeImageInByte)
	
	# print(file.tell())
	# skip the dicom tag (0x7fe0, 0x0010) 4 bytes,
	# then the VR info if we have "explicit VR" (if not, nothing is there in "implicit VR") 4 bytes (if not 0 byte): (VR_OW = 0x574f for example)
	# finally the length of the sequence 4 bytes
	# u16 = struct.unpack('H', file.read(2))[0]
	# print(hex(u16) + " " + str(u16))
	# u16 = struct.unpack('H', file.read(2))[0]
	# print(hex(u16) + " " + str(u16))
	# if dcmInfo.is_implicit_VR == False:
		# s32 = struct.unpack('i', file.read(4))[0]
		# print(hex(s32) + " " + str(s32))
	# s32 = struct.unpack('i', file.read(4))[0]
	# print(hex(s32) + " " + str(s32))
	if dcmInfo.is_implicit_VR == True:
		file.seek(8, io.SEEK_CUR)
	else:
		file.seek(12, io.SEEK_CUR)
	file.seek(_frameId*sizeImageInByte, io.SEEK_CUR)
	package = file.read(sizeImageInByte)
	# print(len(package))
	
	# seems faster than...
	image = array.array(pixelType)
	if sys.version_info < (3,0):
		image.fromstring(package) # DEPRECATED
	else:
		image.frombytes(package)
	# ...this
	# n = dcmInfo.Columns*dcmInfo.Rows
	# image = struct.unpack(str(n)+pixelType, package)
	
	# image = np.array(image).reshape(dcmInfo.Columns, dcmInfo.Rows)
	# print(sizeImageInByte)
	# print(np.array(image).shape)
	# print(np.array(image).dtype)
	image = np.array(image).reshape(dcmInfo.Rows, dcmInfo.Columns)
	
	file.close() # TODO use CloseFile here?
	return image, dcmInfo
	
def GetFloat32DicomFrame(_filename, _frameId, _normalize = NORMALIZE_NO):
	image, dcmInfo = ReadDicomFrame(_filename, _frameId)
	return GetFloat32NormalizedFrame(image, dcmInfo.BitsStored, _normalize)

# save a X-ray sequence into dicom format, _sequence is numpy array with the following shape (NumberOfFrames, Rows, Columns)
def SaveDicomSequence(_filename, _sequence):
	file_meta = Dataset()
	# file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.2'  # CT Image Storage
	file_meta.MediaStorageSOPClassUID = '1.2.3.4.5.1.4.1.1.2'  # need valid UID here for real work
	file_meta.MediaStorageSOPInstanceUID = "1.2.3"  # need valid UID here for real work
	file_meta.ImplementationClassUID = "1.2.3.4"  # need valid UIDs here

	# Create the FileDataset instance (initially no data elements, but file_meta supplied)
	ds = FileDataset(_filename, {}, file_meta=file_meta, preamble=b"\0" * 128)

	# Add the data elements -- not trying to set all required here. Check DICOM standard
	# ds.PatientName = "Test^Firstname"
	# ds.PatientID = "123456"

	# Set the transfer syntax
	ds.is_little_endian = True
	ds.is_implicit_VR = True # implicit VR (0002,0010) TransferSyntaxUID: 1.2.840.10008.1.2
	# ds.is_implicit_VR = False # explicit VR (0002,0010) TransferSyntaxUID: 1.2.840.10008.1.2.1

	# Set creation date/time
	# dt = datetime.datetime.now()
	# ds.ContentDate = dt.strftime('%Y%m%d')
	# timeStr = dt.strftime('%H%M%S.%f')  # long format with micro seconds
	# ds.ContentTime = timeStr

	ds.SamplesPerPixel = 1
	ds.PhotometricInterpretation = "MONOCHROME2"
	ds.PixelRepresentation = 0
	ds.HighBit = 15
	ds.BitsStored = 16
	ds.BitsAllocated = 16
	if sys.version_info < (3,0):
		ds.SmallestImagePixelValue = '\\x00\\x00'
		ds.LargestImagePixelValue = '\\xff\\xff'
	else:
		ds.SmallestImagePixelValue = (0).to_bytes(2, byteorder='little')
		ds.LargestImagePixelValue = (65535).to_bytes(2, byteorder='little')
	ds.Columns = _sequence.shape[2]
	ds.Rows = _sequence.shape[1]
	ds.NumberOfFrames = _sequence.shape[0]
	if _sequence.dtype != np.uint16:
		print("warning _sequence.dtype != np.uint16")
		_sequence = _sequence.astype(np.uint16)
	
	ds.PixelData = _sequence.tostring()
	
	ds.save_as(_filename)

	# Write as a different transfer syntax
	# ds.file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRBigEndian  # XXX shouldn't need this but pydicom 0.9.5 bug not recognizing transfer syntax
	# ds.is_little_endian = False
	# ds.is_implicit_VR = False

	# print("Writing test file as Big Endian Explicit VR", filename2)
	# ds.save_as(filename2)
	
def SaveImage(_path, _buffer):
	# with warnings.catch_warnings():
		# warnings.simplefilter("ignore")
		# ski.io.imsave(_path, _buffer)
	ski.io.imsave(_path, _buffer)

def GrayToRGB(_image):
	image = np.empty((3, _image.shape[0], _image.shape[1]))
	image[0][...] = _image[...]
	image[1][...] = _image[...]
	image[2][...] = _image[...]
	return np.moveaxis(image, 0, -1)

# _image has to be smaller than (_newImageSizeX, _newImageSizeY)
# _image.shape has even numbers
# (_newImageSizeX, _newImageSizeY) has even numbers
def PadImage(_image, _newImageSizeX, _newImageSizeY):
	padX = (_newImageSizeX - _image.shape[1])//2
	padY = (_newImageSizeY - _image.shape[0])//2
	padImage = ski.util.pad(_image, ((padY, padY),(padX, padX)), 'constant', constant_values=0) 
	return padImage, padX, padY

def PtsListToMask(_imageSizeX, _imageSizeY, _ptsList, _dilationStructure = (2,2)):
	coordinates = np.swapaxes(_ptsList, 0, 1)
	# print(coordinates.shape)
	# coordinates = coordinates - 0.5
	# coordinates = np.round(coordinates)
	coordinates = np.floor(coordinates)
	coordinates = coordinates.astype(int)

	ids = np.where(np.logical_and(coordinates[0] < _imageSizeX, coordinates[0] >= 0))
	coordinates = coordinates[:,ids[0]]
	# coordinates[0][coordinates[0] > _imageSizeX - 1] = _imageSizeX - 1
	ids = np.where(np.logical_and(coordinates[1] < _imageSizeY, coordinates[1] >= 0))
	coordinates = coordinates[:,ids[0]]
	# coordinates[1][coordinates[1] > _imageSizeY - 1] = _imageSizeY - 1
	
	# mask = np.zeros((_imageSizeX, _imageSizeY), dtype=np.uint8)
	mask = np.zeros((_imageSizeY, _imageSizeX), dtype=bool)
	mask[coordinates[1], coordinates[0]] = True
	
	structure = np.ones(_dilationStructure)
	mask = ski.morphology.binary_dilation(mask, structure)
	# return mask
	return mask.astype(np.uint8)

def DrawCenterline(_outImage, _centerline, _color = [0., 1., 0.], _deltaColor = [0., -1., 1.], _size = 3., _hls = False):
	# _outImage[...] = MarkerListToMask(SIZE_Y, SIZE_X, centerline, (1,1))[...]
	delta = 1./len(_centerline)
	for coord in _centerline:
		if _hls == True:
			colorRGB = colorsys.hls_to_rgb(_color[0], _color[1], _color[2])
		else:
			colorRGB = _color
		if True:
		# if False:
			rr, cc = ski.draw.circle(int(coord[1]), int(coord[0]), _size)
			ids = np.where(np.logical_and(rr < _outImage.shape[2], rr >= 0))
			rr = rr[ids]
			cc = cc[ids]
			ids = np.where(np.logical_and(cc < _outImage.shape[1], cc >= 0))
			rr = rr[ids]
			cc = cc[ids]
			_outImage[0][rr, cc] = colorRGB[0]
			_outImage[1][rr, cc] = colorRGB[1]
			_outImage[2][rr, cc] = colorRGB[2]
		else:
			_outImage[0, int(coord[1]), int(coord[0])] = colorRGB[0]
			_outImage[1, int(coord[1]), int(coord[0])] = colorRGB[1]
			_outImage[2, int(coord[1]), int(coord[0])] = colorRGB[2]
		_color[0] = Clamp(_color[0] + delta*_deltaColor[0], 0., 1.)
		_color[1] = Clamp(_color[1] + delta*_deltaColor[1], 0., 1.)
		_color[2] = Clamp(_color[2] + delta*_deltaColor[2], 0., 1.)
		# print("_color " + str(_color))