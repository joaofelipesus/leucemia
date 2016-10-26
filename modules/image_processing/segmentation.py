import cv2
import math
import numpy as np
from contour import Contour
from image_chanels import ImageChanels
from filters.otsu_threshold_filter import OtsuThresholdFilter
from filters.flood_fill_filter import FloodFillFilter
from _filters import OtsuThreshold



class Segmentation(object):


	def __init__(self , image_path):
		self.rgb_image = cv2.imread(image_path)
		self.height = self.rgb_image.shape[0]
		self.width = self.rgb_image.shape[1]
		self.contours = []
		self.cell_center = 0
		self.cell_radius = 0
		self.mask = None


	def process(self):                                      
		#faz a segmentacao da celula de interece   
		saturation = ImageChanels(self.rgb_image).hsv('S')                                         #extraido canal relativo a Saturacao
		threshold_image = OtsuThreshold(saturation).process()									   #aplica threshold de OTSU no canal referente a saturacao 
		flooded_image = FloodFillFilter(threshold_image).flood_borders()                           #aplica o filtro flood_fill com o objetivo de remover os objetos colados as extremidades
		opened_image = cv2.morphologyEx(flooded_image, cv2.MORPH_OPEN, np.ones((5,5) , np.uint8))  #aplica operacao morfologica de abertura para remover pequenos pontos brancos (ruidos) presentes na imagem resultante da operacao anterior 
		self.contours , contour_image = Contour().get_contours(flooded_image)                                           #computa uma imagem com os contornos desenhados e uma lista com aas coordenadas dos contornos 
		self.cell_center , self.cell_radius = self.find_interest_cell()                            #computa o ponto central e o raio da celula de interesse 
		if len(self.contours) == 0:                                                                     #se o numero de contornos for igual a zero significa que existe apenas um objeto na imagem opened_image logo a mascara ja esta correta
			self.mask = opened_image
		else:
			self.mask = self.remove_noise_objects(contour_image , threshold_image)
		segmented_image = self.build_mask()
		return segmented_image


	def find_interest_cell(self):
		#recebe os contornos de uma imagem e com base neles retorna o ponto central e o raio da celula de interesse , alem de uma lista com os contornos referente apenas a objetos que nao sejam a celula de interesse. A celula de interesse eh aquela que possui uma menor distancia Euclidiana de seu ponto central em relacao ao ponto central da imagem
		image_center_point = tuple([int(self.height / 2) , int(self.width) / 2])               #descobre o ponto central da imagem
		lowest_index = 0
		lowest_distance = None
		for contour_index in range(0 , len(self.contours)):                                         #itera sobre todos os contornos   
			(x,y) , object_radius = cv2.minEnclosingCircle(self.contours[contour_index])            #aplica a funcao cv2.minEnclosingCircle() que recebe um contorno e reorna o raio e o ponto central para a menor circunferencia  possivel que englobe o objeto referente ao contorno passado como parametro
			distance_to_center = math.sqrt(math.pow((x - image_center_point[1]) , 2) + math.pow(y - image_center_point[1] , 2))   #alcula a distancia Euclidiana para o ponto central do contorno em relacao ao ponto central da imagem , tendo em vista que a celula de interece eh a celula mais proxima ao centro da imagem 
			if lowest_distance == None or distance_to_center < lowest_distance:                #verifia se a distancia do ponto central do contorno e o ponto central da imagem eh menor do que a menor distancia computada anteriormente 
				lowest_index = contour_index
				lowest_distance = distance_to_center
		(x,y),cell_radius = cv2.minEnclosingCircle(self.contours[lowest_index])                     #obtem o ponto central e o raio da menor circunferencia possivel que engloba a celula mais proxima do centro da imagem (celula de interesse)
		cell_radius = int(cell_radius)                                                         #normaliza o tipo de dado referente ao raio da "celula"
		cell_center = (int(x),int(y))                                                          #normaliza o tipo de dado referente ao ponto central da celula
		self.contours.pop(lowest_index)                                                             #remove o contorno da celula de interesse da lista que contem os contornos da imagem 
		return cell_center , cell_radius


	def remove_noise_objects(self , contours_image , threshold_image):
		#metodo com o objetivo de remover qualquer objeto da imagem que nao seja a celula de interesse
		flooded_image = FloodFillFilter(contours_image).flood_region(self.cell_center , value = 255)   #preenche a celula central 
		for contour in self.contours:                                                              #varre todos os contornos e verifica se a celula possui o nucleo vazado , nesse caso ocorre uma excecao que sera corrigida mais pra frente
			(x,y) , object_radius = cv2.minEnclosingCircle(contour)                                #computa o raio e o ponto central do contorno
			object_radius = int(object_radius)                                                     #normaliza o tipo de dado  
			object_center = (int(x),int(y))                                                        #normaliza o tipo de dado
			if (object_center[0] + object_radius > self.cell_center[0] + self.cell_radius and object_center[0] - object_radius < self.cell_center[0] - self.cell_radius) and (object_center[1] + object_radius > self.cell_center[1] + self.cell_radius and object_center[1] - object_radius < self.cell_center[1] + self.cell_radius): #verifica se o nucleo real da celula esta em volta do que foi marcado como nucleo
				opened_image = cv2.morphologyEx(threshold_image , cv2.MORPH_OPEN, np.ones((5,5) , np.uint8))
				return opened_image                                                                #nesse caso excepcional a imagem resultante do threshold de OTSU ja esta correta , eh aplicada uma operacao morfologica de abertura para remover pontos de ruido 
		opened_image = cv2.morphologyEx(flooded_image.copy(), cv2.MORPH_OPEN, np.ones((5,5) , np.uint8))   #remove os contornos de objetos que nao sejam a celula central
		return opened_image


	def build_mask(self):
		#retorna a imagem segmentada , multilpica cada um dos canais RGB pela mascara
		self.mask = cv2.threshold(self.mask,127,1,cv2.THRESH_BINARY)[1]  #usado para criar a mascara composta por valores 1 e 0
		red , green , blue = ImageChanels(self.rgb_image).rgb()
		red = red * self.mask
		green = green * self.mask
		blue = blue * self.mask
		return cv2.merge((blue , green , red)) #remonta os canais da imagem rgb
	