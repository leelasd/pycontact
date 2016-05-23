from mpi4py import MPI
import numpy as np
import MDAnalysis
from mdanalysis import *
import math
import time
glob_start = time.time()
def chunks_old(l, n):
    """Yield successive n-sized chunks from l."""
    ratio = int(math.floor(len(l)/n))
    print 'RATIO', ratio
    current_chunk = 1
    for i in range(0, len(l), ratio):
        if current_chunk == n:
            yield l[i:-1]
        else:
            yield l[i:i+ratio]
        current_chunk += 1

def chunks(seq, num):
  avg = len(seq) / float(num)
  out = []
  last = 0.0

  while last < len(seq):
    out.append(seq[int(last):int(last + avg)])
    last += avg

  return out

def makeKeyArraysFromMaps(map1, map2, contact):
	global type_array,name_array,resid_array,resname_array,segids
	idx1 = contact.idx1
	idx2 = contact.idx2
	counter = 0
	keys1 = []
	for val in map1:
	    if val == 1:
	        if counter == AccumulationMapIndex.index:
	            keys1.append(idx1)
	        elif counter == AccumulationMapIndex.atype:
	            keys1.append(type_array[idx1])
	        elif counter == AccumulationMapIndex.name:
	            keys1.append(name_array[idx1])
	        elif counter == AccumulationMapIndex.resid:
	            keys1.append(resid_array[idx1])
	        elif counter == AccumulationMapIndex.resname:
	            keys1.append(resname_array[idx1])
	        elif counter == AccumulationMapIndex.segid:
	            keys1.append(segids[idx1])
	    else:
	        keys1.append("none")
	    counter += 1
	counter = 0
	keys2 = []
	for val in map2:
	    if val == 1:
	        if counter == AccumulationMapIndex.index:
	            keys2.append(idx2)
	        elif counter == AccumulationMapIndex.atype:
	            keys2.append(type_array[idx2])
	        elif counter == AccumulationMapIndex.name:
	            keys2.append(name_array[idx2])
	        elif counter == AccumulationMapIndex.resid:
	            keys2.append(resid_array[idx2])
	        elif counter == AccumulationMapIndex.resname:
	            keys2.append(resname_array[idx2])
	        elif counter == AccumulationMapIndex.segid:
	            keys2.append(segids[idx2])
	    else:
	        keys2.append("none")
	    counter += 1
	return [keys1, keys2]

def makeKeyFromKeyArrays(key1, key2):
        key = ""
        itemcounter = 0
        for item in key1:
            if item != "none":
                key += AccumulationMapIndex.mapping[itemcounter] + str(item)
            itemcounter += 1
        key += "-"
        itemcounter = 0
        for item in key2:
            if item != "none":
                key += AccumulationMapIndex.mapping[itemcounter] + str(item)
            itemcounter += 1
        return key

def loop_frame(contacts,map1,map2):
	global backbone
	allkeys = []
	results = []
	for frame in contacts:
	    currentFrameAcc = {}
	    for cont in frame:
	        key1, key2 = makeKeyArraysFromMaps(map1, map2, cont)
	        key = makeKeyFromKeyArrays(key1, key2)
	        # global rank
	        # print key, rank
	        if key in currentFrameAcc:
	            currentFrameAcc[key].fscore += cont.weight
	            currentFrameAcc[key].contributingAtomContacts.append(cont)
	            if cont.idx1 in backbone:
	                currentFrameAcc[key].bb1score += cont.weight
	            else:
	                currentFrameAcc[key].sc1score += cont.weight
	            if cont.idx2 in backbone:
	                currentFrameAcc[key].bb2score += cont.weight
	            else:
	                currentFrameAcc[key].sc2score += cont.weight
	        else:
	            currentFrameAcc[key] = TempContactAccumulate(key1, key2)
	            currentFrameAcc[key].fscore += cont.weight
	            currentFrameAcc[key].contributingAtomContacts.append(cont)
	            if cont.idx1 in backbone:
	                currentFrameAcc[key].bb1score += cont.weight
	            else:
	                currentFrameAcc[key].sc1score += cont.weight
	            if cont.idx2 in backbone:
	                currentFrameAcc[key].bb2score += cont.weight
	            else:
	                currentFrameAcc[key].sc2score += cont.weight
	        if not key in allkeys:
	        	allkeys.append(key)
	    results.append(currentFrameAcc)
	return [allkeys,results]

comm = MPI.COMM_WORLD
size = comm.Get_size()
rank = comm.Get_rank()

if rank == 0:
	start = time.time()
	import pickle
	# importDict = pickle.load(open("/Users/mscheurer/Projects/pycontact/pycontact/defaultsession", "rb"))
	importDict = pickle.load(open("/Users/mscheurer/Dropbox/TCBG/ba/data/yeast_proteasome_ubp6_session", "rb"))
	stop = time.time()
	print stop-start
	contResults = importDict["analyzer"][-1]
	trajArgs = importDict["trajectory"]
	all_chunk = list(chunks(contResults,size))
	for rk in range(1,size):
		comm.send(trajArgs, dest=rk,tag=(math.pow(rk,2)+7))
		# comm.send(all_chunk[rk], dest=rk,tag=(math.pow(rk,2)+9))
else:
	all_chunk = None
	rec = time.time()
	trajArgs = comm.recv(source=0,tag=(math.pow(rank,2)+7))
	rec_end = time.time()
	print 'rec',(rec_end-rec),rank
	# all_chunk = comm.recv(source=0,tag=(math.pow(rank,2)+9))
	# [self.resname_array,self.resid_array,self.name_array,self.type_array,self.segids,self.backbone]
	# map1=[1,1,1,1,1]
	# map2=[1,1,1,1,1]
	# start = time.time()
	# results = loop_frame(all_chunk,map1,map2,trajArgs[-1],trajArgs[3],trajArgs[2],trajArgs[1],trajArgs[0],trajArgs[4])
	# stop = time.time()
	# print "time: ", str(stop-start), rank
	# print str(len(all_chunk)), rank
all_chunk = comm.scatter(all_chunk,root=0)
map1=[1,0,0,0,0]
map2=[1,0,0,0,0]
start = time.time()
backbone,type_array,name_array,resid_array,resname_array,segids = trajArgs[-1],trajArgs[3],trajArgs[2],trajArgs[1],trajArgs[0],trajArgs[4]
results = loop_frame(all_chunk,map1,map2)
stop = time.time()
print "time: ", str(stop-start), rank
print str(len(all_chunk)), rank
glob_stop = time.time()
print glob_stop - glob_start
# all_chunk = comm.scatter(all_chunk, root=0)
#print 'rank',rank,'has data:',data
# newData = comm.gather(arguments,root=0)

# if rank == 0:
   # print 'master:',newData
