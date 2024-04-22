function staticImagesCarousel() {
    return {
                translateAmount: 0,
                maxTranslate: 0,
                imageWidth: 0,
                margin: 8,
                updateMaxTranslate() {
                    this.maxTranslate = this.$refs.container.scrollWidth - this.$refs.container.clientWidth;
                },
                updateImageWidth() {
                    const image = this.$refs.container.querySelector('img');
                    if (image) {
                        this.imageWidth = image.offsetWidth + this.margin;
                    }
                },
                decreaseTranslateAmount() {
                    this.translateAmount = Math.max(this.translateAmount - this.imageWidth, 0);
                },
                increaseTranslateAmount() {
                    this.translateAmount = Math.min(this.translateAmount + this.imageWidth, this.maxTranslate);
                },
                resetTranslateAmount() {
                    this.translateAmount = 0;
                }
            }
};

function dynamicImagesCarousel(images) {
    return {
            currentImage: 0,
            images: images,
            init() { this.changeImage(); },
            nextImage() {
                if ( this.hasNext() ) {
                    this.currentImage++;
                } else {
                    this.currentImage = 0;
                }
                this.changeImage();
            },
            previousImage() {
                if ( this.hasPrevious() ) {
                    this.currentImage--;
                    } else {
                    this.currentImage = this.images.length - 1;
                }
                this.changeImage();
            },
            changeImage() {
                this.$refs.mainImage.src = this.images[this.currentImage];
            },
            pickImage(index) {
                this.currentImage = index;
                this.changeImage();
            },
            hasPrevious() {
                return this.currentImage > 0;
            },
            hasNext() {
                return this.images.length > (this.currentImage + 1);
            }
        }
}