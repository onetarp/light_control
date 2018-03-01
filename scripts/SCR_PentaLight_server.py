#!/usr/bin/env python

from light.srv import *
import rospy
import socket
import time
import sys

def initialize():
	config = open('SCR_PentaLight_conf.txt','r')
	lights = []
	addresses = []
	position_array = []

	#read addresses
	for line in config:
		line = line.rstrip()
		if line == '-': break
		addresses.append(line)

	#read position array
	first = True
	for line in config:
		line = line.rstrip()
		#read the first line seperately to create initial lists
		if first:
			for char in line:
					col = []
					col.append(int(char))
					position_array.append(col)
			first = False
		else:
			i = 0
			for char in line:
				position_array[i].append(int(char))
				i += 1
	
	config.close()

	#get light coordinates from array
	light_coords = []
	for i in range(len(position_array)):
		for j in range(len(position_array[i])):
			if position_array[i][j] == 1:
				light_coords.append((i,j))
	print light_coords

	if len(light_coords) != len(addresses):
		print ("Error: There are %s addresses and %s lights in the array"%(len(addresses),len(light_coords)))
		sys.exit(1)
	
	#create dictionary with coord as key and address as value
	lights = {}
	for i in range(len(light_coords)):
		lights[light_coords[i]] = addresses[i]

	return lights

def initialize_CCT():
	vals = open("SCR_PentaLight_CCT.txt",'r')
	CCT_vals = []
	light_vals = []

	first_line = True
	for line in vals:
		if first_line:
			first_line = False
		else:
			line = line.rstrip();
			split = line.split("\t")
			first = True
			temp_light_vals = []
			for el in split:
				if first:
					CCT_vals.append(int(el))
					first = False
				else:
					temp_light_vals.append(float(el))
			light_vals.append(temp_light_vals)

	vals.close()
	
	CCT_dict = {}
	for i in range(len(CCT_vals)):
		CCT_dict[CCT_vals[i]] = light_vals[i]

	#ragbw
	return CCT_dict

def initialize_int():
	vals = open("SCR_PentaLight_int.txt","r")
	ints = []
	for line in vals:
		line = line.rstrip()
		split = line.split("\t")
		ints.append(split)
	vals.close()

	#bgarw
	return ints

def gen_cmdstr_CCT(state,intensity,CCT_dict,int_list)
	#blue = green = amber = red = white  = "0000"

	send_blue = CCT_dict[state][3]
	send_green = CCT_dict[state][2]
	send_amber = CCT_dict[state][1]
	send_red = CCT_dict[state][0]
	send_white = CCT_dict[state][4]

	intensity = float(intensity)/100

	intens_b = int_list[0][0]*intensity*intensity+int_list[0][1]*intensity
	intens_g = int_list[1][0]*intensity*intensity+int_list[1][1]*intensity
	intens_a = int_list[2][0]*intensity*intensity+int_list[2][1]*intensity
	intens_r = int_list[3][0]*intensity*intensity+int_list[3][1]*intensity
	intens_w = int_list[4][0]*intensity*intensity+int_list[4][1]*intensity

	blue = str(int(65535*send_blue*intens_b))
	green = str(int(65535*send_green*intens_g))
	amber = str(int(65535*send_amber*intens_a))
	red = str(int(65535*send_red*intens_r))
	white = str(int(65535*send_white*intens_w))

	return "PS"+blue+green+amber+red+white

def gen_cmdstr_ragbw(req):
	blue = str(int(65535*(req.blue/100)))
	green = str(int(65535*(req.green/100)))
	amber = str(int(65535*(req.amber/100)))
	red = str(int(65535*(req.red/100)))
	white = str(int(65535*(req.white/100)))

	return "PS"+blue+green+amber+red+white

def handle_CCT(req,lights,CCT_dict,int_list):
	port = 57007

	CCT = 1800
	intensity = 100

	if(req.CCT < 1800):
		CCT = 1800
	elif (req.CCT > 10000):
		CCT = 10000
	else:
		CCT = req.CCT - req.CCT%100

	if (req.intensity < 0):
		intensity = 0
	elif (req.intensity > 100):
		intensity = 100
	else:
		intensity = req.intensity

	cmdstr = gen_cmdstr_CCT(CCT,intensity,CCT_dict,int_list)

	if not (req.x,req.y) in CCT_dict:
		return "Error: No light at specified coordinates"

	address = lights[(req.x,req.y)]

	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect((address,port))
	except ConnectionRefusedError:
		rs = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		rs.connect((address,57011))
		print("Connection refused on " + req.address)

	s.send(cmdstr)
	a = s.recv(1024)
	time.sleep(0.001)

	s.shutdown(socket.SHUT_RDWR)
	s.close()
	
	return PentaLight_CCTResponse(cmdstr)

# def handle_int(req,lights):
# 	return

def handle_ragbw(req,lights):
	port = 57007

	cmdstr = gen_cmdstr_ragbw(req)

	if not (req.x,req.y) in CCT_dict:
		return "Error: No light at specified coordinates"

	address = lights[(req.x,req.y)]

	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect((address,port))
	except ConnectionRefusedError:
		rs = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		rs.connect((address,57011))
		print("Connection refused on " + req.address)

	s.send(cmdstr)
	a = s.recv(1024)
	time.sleep(0.001)

	s.shutdown(socket.SHUT_RDWR)
	s.close()

	return PentaLight_ragbwResponse(cmdstr)

def PentaLight_server(lights,CCT_dict,int_list):
	rospy.init_node("PentaLight_server")

	CCT_service = rospy.Service(
		"CCT", 
		PentaLight_CCT, 
		lambda msg: handle_CCT(msg,lights,CCT_dict,int_list))

	# intensity_service = rospy.Service(
	# 	"intensity", 
	# 	PentaLight_int, 
	# 	lambda msg: handle_int(msg,lights,int_list))

	ragbw_service = rospy.Service(
		"ragbw", 
		PentaLight_ragbw, 
		lambda msg: handle_ragbw(msg,lights))

if (__name__ == "__main__"):
	lights = initialize()
	CCT_dict = initialize_CCT()
	int_list = initialize_int()
	PentaLight_server(lights,CCT_dict,int_list)

