# Vimeo Programming Challenge

Code for Vimeo Programming Challenge for the Summer 2018 Internship position.

## Installation
This script requires Python, Gevent, and PyCurl. 


PyCurl is a Python wrapper around cURL, which is an application library used to download files or coordinate requests on the web. Installation of PyCurl can be done as follows:

  `$ pip install pycurl`

Gevent is a Python networking library built upon the concepts of coroutines. *Coroutines* are components that generalize subroutines that allow multiple entry points for suspending and resuming execution at certain locations, which shines when developing ways to safely download large files. Installation of Gevent can be done as follows:

   `$ pip install gevent` 

## Usage

The script requires the user to provide the URL to download the remote file via commandline. The script can be run in command line by 

`$ python coding_challenge.py URL`

The script also supports modifying the number of processes to be used to download the file by using the `-c` or `--count` flags:

`$ python coding_challenge.py URL -c NUMBER_THREADS`

By default, the script will use 8 processes.

##Approach

In this script, I utilized Greenlets to create a concurrency supporting file downloader. Within my class, I create an intial instance of my class that holds the various values that can be used to allow and monitor the file download. Following this instantiation, my script then checks whether this download is resuming from a previous cancellation. Following this check, my script will then begin fetching the file by spawning the number of processes specified by the user assuming the server supports byte range GET requests, else it spawns a single process. Following this spawn, each process will work concurrently reading each chunk from the remote file and copying it to the local file. Once all the concurrent downloads have finished, the script will then stitch all the chunks together by writing to the local file, and then comparing the checksums of the remote and local file. Should the checksums be different, the script will send an error and delete the file.

## FAQ

**Q.** Why use Gevent instead of Python's Multiprocessing Library?

**A.** In this script, I decided against using Python Multiprocessing and threads due to the fact that Gevent has a significantly lower overhead than threads, due to the fact that creating a thread requires creating a separate space within Virtual Memory and additonal Kernel Overhead. In addition, Gevent allows for synchronous interactions as each *Greenlet* developed will work in its individual context, which is useful when dealing with concurrency problems, such as downloading bytes in parts.

**Q.** Why use Python instead of C for networking?

**A.** While C has long been the backbone for networking applications, the language itself is often a pain to develop in, especially when dealing with networking applications due to it's verbosity. For example, whereas in Python one can automatically form a request using the `urllib2` and `requests` libraries, one would have to specify multiple different flags and structs in order to create a basic request. As such, I found Python's syntax to be more succinct in comparison to C when dealing with networking applications.