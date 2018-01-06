#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

from gevent import monkey
from gevent.pool import Pool
monkey.patch_all()

import os
import re
import md5
import sys
import glob
import time
import pycurl
import signal
import timeit
import urllib2
import hashlib
import argparse
import requests
import cStringIO
import fileinput


def hash_url(url, max_file_size=100*1024*1024):
    remote = urllib2.urlopen(url)
    hash = hashlib.md5()

    total_read = 0
    while True:
        data = remote.read(4096)
        total_read += 4096

        if not data or total_read > max_file_size:
            break

        hash.update(data)

    return hash.hexdigest()


def catch_ctrl_c(signum, frame):
    print()
    sys.exit(0)


class downloader(object):
	def __init__(self):
	    signal.signal(signal.SIGINT, catch_ctrl_c)

	    self.count = 8
	    self.url = None
	    self.speed = 0
	    self.total_time = 0

	    self.partial = False
	    self.content_length = 0
	    self.hash = 0
	    self.start = 0
	    self.startcount = []
	    self.filename = None
	    self.chunk_size = 0
	    self.chunks = []
	    self.files = []

	def parse_args(self):
	    parser = argparse.ArgumentParser()
	    parser.add_argument('url')
	    parser.add_argument('-c', '--count', type = int, default = self.count)
	    args = parser.parse_args()
	    self.url = args.url
	    self.count = args.count
	    return args

	def byte_range(self, url):
	    curl = pycurl.Curl()
	    header = cStringIO.StringIO()

	    curl.setopt(c.URL, url)
	    curl.setopt(c.NOBODY, 1)
	    curl.setopt(c.HEADERFUNCTION, header.write)
	    curl.perform()
	    curl.close()

	    header_text = header.getvalue()
	    header.close()

	    verbose_print(header_text)

	    match = re.search('Accept-Ranges:\s+bytes', header_text)
	    if match:
	        return True
	    else:
	        match = re.search('Accept-Ranges:\s+none', header_text)
	        if match:
	            return False
	        else:
	            curl = pycurl.Curl()
	            curl.setopt(curl.RANGE, '0-0')
	            curl.setopt(curl.URL, url)
	            curl.setopt(curl.NOBODY, 1)
	            curl.perform()

	            http_code = curl.getinfo(curl.HTTP_CODE)
	            curl.close()


	def get_file_info(self):
	    r = requests.head(self.url)
	    self.content_length = int(r.headers.get('Content-Length', 0))
	    self.hash = hash_url(self.url)
	    self.partial = byte_range(self.url)

	    if (self.partial == True):
		    self.chunk_size = self.content_length / self.count
		    for i in range(self.count):
		        if i == self.count - 1:
		            boundary = self.content_length
		        else:
		            boundary = ((i + 1) * self.chunk_size) - 1
		        self.chunks.append((i * self.chunk_size, boundary))
		else:
			self.chunk_size = self.content_length
			boundary = self.content_length
			self.chunks.append((self.chunk_size, boundary))

	    self.filename = os.path.basename(self.url)
	    while os.path.isfile(self.filename):
	        prefix, ext = os.path.splitext(self.filename)
	        if ext[1:].isdigit():
	            newfile = int(ext[1:]) + 1
	            self.filename = '%s.%s' % (prefix, newfile)
	        else:
	            self.filename = '%s.0' % self.filename

	def resume_check(self):
	    globs = glob.glob('%s.part*' % self.filename)
	    if len(globs) == self.count:
	        sizes = []
	        new_chunks = []
	        for i, f in enumerate(globs):
	            sizes.append(os.path.getsize(f))
	            if sizes[-1] == self.chunk_size:
	                new_chunks.append(None)
	                self.startcount.append(sizes[-1])
	            elif (sizes[-1] != self.chunks[i][1] and sizes[-1] < self.chunk_size):
	                new_chunks.append((self.chunks[i][0] + sizes[-1], ((i + 1) * self.chunk_size) - 1))
	                self.startcount.append(sizes[-1])
	            else:
	                print('%s < %s' % (sizes[-1], self.chunks[i][1] - self.chunks[i][0]))
	                print('partial files already exist, and do not match the size range')
	                print('    %s' % '\n    '.join(globs))
	                sys.exit(1)

	        self.chunks[:] = new_chunks
	    elif globs:
	        print('partial files already exist, and do not match the count (%s) specified:' % self.count)
	        print('    %s' % '\n    '.join(globs))
	        print('\nTry setting -c %s' % len(globs))
	        sys.exit(1)

	def print_start(self):
	    print('Downloading from %s' % self.url)
	    print('File size: %s bytes' % self.content_length)
	    print('Output file: %s' % self.filename)
	    if self.startcount:
	        print('Resuming download\n')
	    else:
	        print('Starting download\n')

	def download(self, filename, chunk, bytecount):
	    headers = { 'Range': 'bytes=%s-%s' % chunk }
	    r = requests.get(self.url, headers = headers, stream = True)
	    with open(filename, 'a') as f:
	        for block in r.iter_content(4096):
	            if not block:
	                break
	            bytecount.append(len(block))
	            f.write(block)
	            f.flush()

	def print_progress(self, pool, bytecount):
	    while 1:
	        time.sleep(0.1)

	        total = float(sum(bytecount))
	        if not total:
	            continue

	        if pool.free_count() == pool.size:
	            break

	        self.speed = total/(timeit.default_timer() - self.start)
	        remaining = self.content_length - total - sum(self.startcount)
	        percent = \
	            ((total + sum(self.startcount)) / self.content_length) * 100
	        sys.stdout.write('\r[%3.00f%%] %7.02f MB/s [%4.00fs] ' % (percent, self.speed/1024**2, remaining/self.speed))
	        sys.stdout.flush()

	def fetch(self):
	    bytecount = []
	    self.start = timeit.default_timer()
	    children = Pool(size = self.count)

	    parent = Pool(size = 1)
	    parent.spawn(self.print_progress, children, bytecount)
	    
	    for i, chunk in enumerate(self.chunks):
	        self.files.append('%s.part%03d' % (self.filename, i))
	        if not chunk:
	            continue
	        children.spawn(self.download, self.files[-1], chunk, bytecount)

	    children.join()
	    self.total_time = timeit.default_timer() - self.start
	    print()

	def stitch(self):
	    with open(self.filename, 'w') as f:
	        for block in fileinput.input(self.files, bufsize=4096):
	            f.write(block)
	            f.flush()

	    for f in self.files:
	        os.unlink(f)

		if hashlib.md5(open(self.filename,'rb').read()).hexdigest() != self.hash:
			os.remove(self.filename)
			print("Download failed - different checksum")

	def print_final(self):
	    print('\nDownloaded %.00f MB in %.00f seconds. (%.02f MB/s)' % (self.content_length/1024**2, self.total_time, self.speed/1024**2))


if __name__ == '__main__':
    down = downloader()
    down.parse_args()
    down.get_file_info()
    down.resume_check()
    down.print_start()
    down.fetch()
    down.stitch()
    down.print_final()
