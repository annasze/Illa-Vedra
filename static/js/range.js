function range(priceObj) {

    return {
      minPrice: parseInt(priceObj[0]) || 1,
      maxPrice: parseInt(priceObj[1]) || 10000,
      min: 1,
      max: 10000,
      minThumb: 0,
      maxThumb: 0,

      minTrigger() {
        this.minPrice = parseInt(this.minPrice);
        if (isNaN(this.minPrice) || this.minPrice < this.min) {
          this.minPrice = this.min;
        }
        this.minPrice = Math.min(this.minPrice, this.maxPrice - 10);
        this.minThumb = ((this.minPrice - this.min) / (this.max - this.min)) * 100;
        priceObj[0] = this.minPrice;
      },

      maxTrigger() {
        this.maxPrice = parseInt(this.maxPrice);
        if (isNaN(this.maxPrice) || this.maxPrice > this.max) {
          this.maxPrice = this.max;
        }
        this.maxPrice = Math.max(this.maxPrice, this.minPrice + 10);
        this.maxThumb = 100 - (((this.maxPrice - this.min) / (this.max - this.min)) * 100);
        priceObj[1] = this.maxPrice;
      },
      setMaxPrice(maxPrice) {
        this.max = parseInt(maxPrice);
        if (this.max < this.maxPrice) {
            this.maxPrice = this.max
            }
        }
    }
}