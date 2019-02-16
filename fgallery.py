from flask import Flask, render_template, send_file, abort, url_for, redirect, request
from PIL import Image
#import pyexiv2
from libxmp.utils import file_to_dict
from libxmp import consts
import os, glob
from datetime import datetime

gallerySource="/srv/http/photo/galleryjpegs"
galleryThumbs="/srv/http/photo/gallerythumbs"

application = Flask(__name__)

@application.route('/')
def rendergallery():
    return redirect(url_for('getalbum', imgFolder="00 Portfolio"))
    #return request.base_url + url_for('getalbum', imgFolder="00 Portfolio")

@application.route('/getalbum/<path:imgFolder>')
def getalbum(imgFolder):

    albumSourceDir=gallerySource + '/' + imgFolder

    if not os.path.exists(albumSourceDir):
        abort(404)

    ############################################################
    ##### Populate Menu with a list of directories in the source
    ############################################################
    prevlevel = 0
    currentlevel = 0
    menuHtml = []

    rootdir = gallerySource + '/'
    #the level of the directory is the count of slashes in it
    rootlevel = rootdir.count('/') + 1

    # traverse root directory, and list directories as dirs and files as files
    for root, dirs, files in os.walk(rootdir,followlinks=True):
        #we want the directories to be sorted
        dirs.sort()

        #for the top level to be zero, we need to subtract the level of the root directory
        currentlevel = root.count('/') - rootlevel + 1

        if currentlevel < prevlevel:
            #need to close all of the <ul> tags
            x = prevlevel
            while x != currentlevel:
                menuHtml.append(x * '  '+ '</li></ul>')
                x = x - 1

        if dirs and os.path.basename(root) != "":
            menuHtml.append('<li>' + os.path.basename(root) + '<ul>')

        if currentlevel > prevlevel:
            #level up (will only go up one level at a time
            menuHtml.append(currentlevel * '  ')

        if not dirs and os.path.basename(root) != "":
            menuHtml.append(currentlevel * '  '
                    +'  <li><a href="/getalbum/' 
                    + root.replace(rootdir, '')
                    + '">'
                    + os.path.basename(root)
                    + '</a></li>')
            prevlevel = currentlevel
    x = currentlevel
    while x != 0:
        menuHtml.append(x * '  '+ '</ul></li>')
        x = x - 1

    returnVal=""

    imgFiles=glob.glob(albumSourceDir + '/*.jpg')
    imgFiles.sort(reverse=True)

    flinks=list()

    for imgFile in imgFiles:
        #metadata=pyexiv2.ImageMetadata(imgFile)
        #metadata.read()
        #imgDesc = metadata['Xmp.dc.title'].value['x-default'] \
        #         + " (" \
        #         + metadata['Exif.Image.DateTimeOriginal'].value.strftime('%B %Y') \
        #         + ")"
        # Feb 2019 - pyexiv2 is just a pain to maintain for just the one (title) tag
        #            Moved to PIL.Image and libxmp.utils.file_to_dict / libxmp.consts
        try:
            xmp = file_to_dict(imgFile)
            imgTitle = xmp[consts.XMP_NS_DC][1][1]
        except:
            imgTitle = ''
        try:
            dtText = Image.open(imgFile)._getexif()[36867]
            dtDate = datetime.strptime(dtText, '%Y:%m:%d %H:%M:%S')
            imgDateTime = dtDate.strftime('%B %Y')
        except:
            imgTitle = ''
        imgDesc = imgTitle \
                 + " (" \
                 + imgDateTime \
                 + ")"
        flinks.extend([ {"sml" : url_for('getimg', imgFolder=imgFolder, imgSize='sml', imgFile=os.path.basename(imgFile)),
                         "med" : url_for('getimg', imgFolder=imgFolder, imgSize='med', imgFile=os.path.basename(imgFile)),
                         "desc": imgDesc }])

    return render_template('gallery.html',flinks=flinks, menuHtml=menuHtml)

@application.route('/getimg/<path:imgFolder>/<imgSize>/<imgFile>')
def getimg(imgFolder,imgSize,imgFile):

    if imgSize == "sml":
        targetWidth=600
        targetHeight=600
        targetQuality=50
    elif imgSize == "med":
        targetWidth=1920
        targetHeight=1080
        targetQuality=90

    #generate source and target file names
    origFile=gallerySource + "/" + imgFolder + "/" + imgFile
    targetDir=galleryThumbs + "/" + imgSize + "/" + imgFolder 
    targetFile=targetDir + "/" + imgFile

    #return 404 if origFile doesn't exist
    # or incorrect imgSize
    if not os.path.exists(origFile) \
      or imgSize not in ("med","sml","org"):
        abort(404)

    regenerate=False

    #regenerate images for non-original-file requests where
    #  target file doesn't exist or is older than original; or
    #  target file exists but has incorrect dimensions
    if imgSize != "org":
        if not os.path.exists(targetFile) \
        or os.path.getmtime(targetFile) < os.path.getmtime(origFile) :
            regenerate=True             
        else :
            with Image.open(targetFile) as img:
                width, height = img.size
                if width != targetWidth and height != targetHeight :
                    regenerate=True

    if regenerate :
        #create target directory if it doesn't exist
        if not os.path.exists(targetDir) : os.makedirs(targetDir)

        #regenerate the image file
        with Image.open(origFile) as img:
            img.thumbnail(size=[targetWidth, targetHeight], resample=Image.LANCZOS)
            img.save(fp=targetFile, quality=targetQuality)

    return send_file(targetFile,mimetype='image/jpeg')

if __name__ == "__main__":
    application.run(host='0.0.0.0')
