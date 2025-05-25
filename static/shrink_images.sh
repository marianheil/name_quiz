#! /bin/bash
mogrify -path images_small -resize 400x400\> -format jpg images/*.jpg
