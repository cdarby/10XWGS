#!/usr/bin/env python

# Copyright (c) 2016 Ryan Collins <rcollins@chgr.mgh.harvard.edu>
# Distributed under terms of the MIT license.

"""
Estimate original molecule sizes and coordinates from 10X linked-read WGS barcodes
"""

import argparse
from collections import defaultdict, Counter, namedtuple
import pysam

def get_gemcode_regions(ibam, dist):
    """
    Estimates molecule coordinates from colinear reads with overlapping 10X barcodes

    Parameters
    ----------
    ibam : pysam.AlignmentFile
        Input 10X bam
    dist : int
        Partitioning distance (bp) for separating reads with overlapping
        barcodes into independent fragments

    Yields
    ------
    region : namedtuple
        chr, start, end, barcode, readcount
    """

    #Create namedtuples for storing read coordinate and molecule info
    coords = namedtuple('coords', ['chr', 'pos'])
    molecule = namedtuple('molecule', ['chr', 'start', 'end', 'barcode', 'readcount'])

    #Create defaultdict for storing gemcode tuples
    #Key is gemcodes, value is coords namedtuple
    gemcodes = defaultdict(list)

    #Iterate over reads in bamfile
    for read in ibam:
        #Save 10X barcode for read as gem
        gem = read.get_tag('RX')
        #If barcode has been seen previously and new read is either from different
        #contig or is colinear but beyond dist, yield old barcode as interval
        #before adding new read to list
        if gem in gemcodes and (gemcodes[gem][-1].chr != read.reference_name or 
                                read.reference_start - gemcodes[gem][-1].pos > dist):

            yield molecule(gemcodes[gem][0].chr, 
                           min([pos for chr, pos in gemcodes[gem]]), 
                           max([pos for chr, pos in gemcodes[gem]]), 
                           gem, len(gemcodes[gem]))

            gemcodes[gem] = [coords(read.reference_name, read.reference_start)]

        else:
            #Else just add read to preexisting dictionary 
            gemcodes[gem].append(coords(read.reference_name, read.reference_start))

    #Write out all remaining molecules at end of bam
    for gem in gemcodes:
        yield molecule(gemcodes[gem][0].chr, min([pos for chr, pos in gemcodes[gem]]), max([pos for chr, pos in gemcodes[gem]]), gem, len(gemcodes[gem]))

#Run
def main():
    #Add arguments
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ibam', type=pysam.AlignmentFile,
                        help='Input bam')
    parser.add_argument('outfile', help='Output bed file')
    parser.add_argument('-d', '--dist', type=int, default=50000,
                        help='Molecule partitioning distance in bp (default: 50000)')
    args = parser.parse_args()

    #Open outfile
    fout = open(args.outfile, 'w')

    #Get gemcode regions
    for bed in get_gemcode_regions(args.ibam, args.dist):
        #Turn molecule object into string
        bed_str = '{0}\t{1}\t{2}\t{3}\t{4}'.format(bed.chr, bed.start, bed.end, bed.barcode, bed.readcount)

        #Write to file
        fout.write(bed_str + '\n')

    #Close outfile
    f.close()

if __name__ == '__main__':
    main()