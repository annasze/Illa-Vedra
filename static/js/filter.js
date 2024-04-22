function filters() {
    return {
        color: [],
        size: [],
        price: [],
        sorting: '',
        toggleFilter(arr, fieldName) {
            const index = arr.indexOf(fieldName);
            index != -1 ? arr.splice(index, 1) : arr.push(fieldName);
        },
        parseValues(paramName) {
            const urlParams = new URLSearchParams(window.location.search);
            const myParam = urlParams.get(paramName);
            if (myParam) {
                return myParam.split(",");
            } else {
                return []
                }
        },
        setColor() {
             this.color = this.parseValues('color')
        },
        setSize() {
             this.size = this.parseValues('size')
        },
        setSorting() {
            const arr = this.parseValues('sorting');
            this.sorting = arr[0] || ''
        },
        setPrice() {
            const priceLte =  parseInt(this.parseValues('price_lte'));
            const priceGte =  parseInt(this.parseValues('price_gte'));

            this.price = [priceGte, priceLte]
        },
        redirect(newParamsObj) {
            const urlObj = new URL(window.location.href);
            const params = new URLSearchParams(urlObj.search);

            for (let key in newParamsObj) {

                if (newParamsObj[key] === '') {
                    params.delete(key);
                } else {
                    const values = newParamsObj[key].split(',');
                    params.set(key, values.join(','));
                }
            };

            urlObj.search = params.toString();
            window.location.href = urlObj.toString();
        },
        redirectToPath() {
            window.location.href = window.location.pathname
            },
        newParams() {
            return {
                "color": this.color.join(','),
                "size": this.size.join(','),
                'price_gte': this.price[0].toString(),
                'price_lte': this.price[1].toString(),
                'sorting': this.sorting
            }
        }
    }
}









