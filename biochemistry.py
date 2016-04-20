import collections
import numpy as np
from read_db import *
compare = lambda x, y: collections.Counter(x) == collections.Counter(y)

# TODO: remove, deprecated
class ResidueType:
    positive, negative, nonpolar, polar, other = range(5)
    mapping = {"asp": negative, "arg": positive, "lys": positive, "glu": negative}

class ContactType:
    saltbr, hydrophobic, hbond, other = range(4)
    colors = ["rgba(255, 0,0, 50)", "rgba(0, 0,255, 50)", "rgba(255, 0 ,255, 50)", "rgba(255, 255 ,255, 50)"]

class HBondType:
    none, donor, acceptor, both = range(4)
    mapping = {"none": none, "don": donor, "acc": acceptor, "both": both}

class SideChainPolarity:
    nonpolar, positive, negative, polar = range(4)
    mapping = {"nonpolar": nonpolar, "positive": positive, "negative": negative, "polar": polar}

class BackboneSidechainType:
    contactsBb, contactsSc = range(2)


class BackboneSidechainContactType:
    bb_only, sc_only, both = range(3)
    mapping = [[BackboneSidechainType.contactsBb, BackboneSidechainType.contactsBb],[BackboneSidechainType.contactsBb, BackboneSidechainType.contactsSc], [BackboneSidechainType.contactsSc, BackboneSidechainType.contactsSc]]
    colors = [[0,200,200],[200,200,0],[0,200,0]]


class Residue:
    def __init__(self, name, bb, sc):
        self.name = name.lower()
        self.bb = float(bb)
        self.sc = float(sc)
        if self.bb > self.sc:
            self.contactsBy = BackboneSidechainType.contactsBb
        else:
            self.contactsBy = BackboneSidechainType.contactsSc
        # TODO: propably init db first and just call select (speed up)
        #sidechain polarity
        scpol = str(read_residue_db("scpolarity","name",self.name)[0]["scpolarity"])
        self.scpolarity = SideChainPolarity.mapping[scpol]
        #hydrogen bonds: donor, acceptor, both
        hbond = str(read_residue_db("hbondtype", "name", self.name)[0]["hbondtype"])
        self.hbondtype = HBondType.mapping[hbond]
        # self.printself()

    def printself(self):
        print(self.name + " " + str(self.contactsBy) + " " + str(self.scpolarity) + " " + str(self.hbondtype))

class Contact:
    def __init__(self, resA, residA, resB, residB, bb1, sc1, bb2, sc2, scoreArray):
        self.resA = resA
        self.resB = resB
        self.residA = residA
        self.residB = residB
        self.scoreArray = scoreArray
        self.title = self.resA + self.residA + " - " + self.resB + self.residB
        self.residueA = Residue(self.resA,bb1,sc1)
        self.residueB = Residue(self.resB,bb2,sc2)
        self.contactType = self.determine_ctype()
        self.determineBackboneSidechainType()
        self.mean_score()
        self.median_score()

    def determineBackboneSidechainType(self):
        if compare([self.residueA.contactsBy, self.residueB.contactsBy], BackboneSidechainContactType.mapping[BackboneSidechainContactType.bb_only]):
            self.backboneSideChainType =  BackboneSidechainContactType.bb_only
        elif compare([self.residueA.contactsBy, self.residueB.contactsBy], BackboneSidechainContactType.mapping[BackboneSidechainContactType.sc_only]):
            self.backboneSideChainType = BackboneSidechainContactType.sc_only
        else:
            self.backboneSideChainType = BackboneSidechainContactType.both

    def framenumber(self):
        return len(self.scoreArray)

    def total_time(self, ns_per_frame, threshold):
        time = 0
        for score in self.scoreArray:
            if score > threshold:
                time += ns_per_frame
        self.ttime = time
        return self.ttime

    def mean_score(self):
        mean = 0
        for score in self.scoreArray:
            mean += score
        mean = mean / len(self.scoreArray)
        self.meanScore = mean
        return mean

    def median_score(self):
        med = np.median(self.scoreArray)
        self.medianScore = med
        return med

    def determine_ctype(self):
        a = self.residueA
        b = self.residueB
        # check if both residues contact by backbone
        if a.contactsBy == BackboneSidechainType.contactsBb and b.contactsBy == BackboneSidechainType.contactsBb:
            return ContactType.hbond

        # check if contact by sidechain and backbone
        if (a.contactsBy == BackboneSidechainType.contactsBb and b.contactsBy == BackboneSidechainType.contactsSc):
            # sc contact by residue B
            if b.hbondtype != HBondType.none:
                return ContactType.hbond
            else:
                return ContactType.other
        elif (a.contactsBy == BackboneSidechainType.contactsSc and b.contactsBy == BackboneSidechainType.contactsBb):
            # sc contact by residue A
            if a.hbondtype != HBondType.none:
                return ContactType.hbond
            else:
                return ContactType.other

        if a.contactsBy == BackboneSidechainType.contactsSc and b.contactsBy == BackboneSidechainType.contactsSc:
            # check for saltbridge
            if (a.scpolarity == SideChainPolarity.positive and b.scpolarity == SideChainPolarity.negative) or \
                (b.scpolarity == SideChainPolarity.positive and a.scpolarity == SideChainPolarity.negative):
                return ContactType.saltbr

            # check for hydrophobic contact
            if a.scpolarity == SideChainPolarity.nonpolar and b.scpolarity == SideChainPolarity.nonpolar:
                if a.hbondtype == HBondType.none or b.hbondtype == HBondType.none:
                    return ContactType.hydrophobic

            # final hbond scan

            if (a.hbondtype == HBondType.donor and b.hbondtype == HBondType.acceptor) or \
                (a.hbondtype == HBondType.acceptor and b.hbondtype == HBondType.donor) or \
                (a.hbondtype == HBondType.both and b.hbondtype == HBondType.both) or \
                (a.hbondtype == HBondType.donor and b.hbondtype == HBondType.both) or \
                (a.hbondtype == HBondType.both and b.hbondtype == HBondType.donor) or \
                (a.hbondtype == HBondType.acceptor and b.hbondtype == HBondType.both) or \
                (a.hbondtype == HBondType.both and b.hbondtype == HBondType.acceptor):
                    return ContactType.hbond

            return ContactType.other

def mean_score_of_contactArray(contacts):
    meanList = []
    for c in contacts:
        meanList = np.concatenate((meanList, c.scoreArray), axis=0)
    return np.mean(meanList)

def median_score_of_contactArray(contacts):
    medianList = []
    for c in contacts:
        medianList = np.concatenate((medianList,c.scoreArray),axis=0)
    return np.median(medianList)