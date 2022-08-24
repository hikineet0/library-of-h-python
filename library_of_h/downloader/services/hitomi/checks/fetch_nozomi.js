function fetch_nozomi() {
        var filepath = decodeURIComponent(document.location.href.replace(/.*hitomi\.la\//, ''));
        if (!filepath) {
                tag = 'index';
                language = 'all';
                page_number = 1;
        } else if (/^\?page=\d+$/.test(filepath)) {
                tag = 'index';
                language = 'all';
                
                page_number = parseInt(filepath.replace(/.*\?page=(\d+)$/, '$1'));
                if (!page_number || page_number < 1) return;
        } else {
                if (/\?page=\d+$/.test(filepath)) {
                        page_number = parseInt(filepath.replace(/.*\?page=(\d+)$/, '$1'));
                        if (!page_number || page_number < 1) return;
                }
                
                var elements = filepath.replace(/\.html(?:\?page=\d+)?$/, '').split('-');
                if (elements.length < 2) return;
                while (elements.length > 2) {
                        elements[1] = elements[0] + '-' + elements[1];
                        elements.shift();
                }
                //[series/popular/today/female:filming, german]
                //[popular/today, czech]

                tag = elements[0];
                //series/popular/today/female:filming
                //popular/today
                if (/\//.test(tag)) {
                        var area_elements = tag.split(/\//);
                        //[series, popular, today, female:filming]
                        //[popular, today]
                        if (area_elements[1] === 'popular') {
                                popular = area_elements[2];
                                //today
                                area_elements.splice(1, 2); //delete elements 2 and 3
                                //[series, female:filming]
                        } else if (area_elements[0] === 'popular') {
                                popular = area_elements[1];
                                //today
                        }
                        if (area_elements.length !== 2) return;

                        area = area_elements[0];
                        //series
                        //popular
                        if (!area || /[^A-Za-z0-9_]/.test(area)) return;
        
                        tag = area_elements[1];
                        //female:filming
                        //today
                }
                if (!tag || /[^A-Za-z0-9_: .-]/.test(tag)) return;

                language = elements[1];
                if (!language || /[^A-Za-z]/.test(language)) return;
        }
        
        tag_display = tag.replace(/(?:fe)?male:/, '');
        if (area === 'popular') {
                tag_display = 'popular ('+tag+')';
        }
        
        var nozomi_address = '//'+[domain, [tag, language].join('-')].join('/')+nozomiextension;
        if (area) {
                nozomi_address = '//'+[domain, area, [tag, language].join('-')].join('/')+nozomiextension;
                if (popular && area !== 'popular') { //series/popular/today/female:filming-german
                        nozomi_address = '//'+[domain, area, 'popular', popular, [tag, language].join('-')].join('/')+nozomiextension;
                }
        }
        
        var start_byte = (page_number - 1) * galleries_per_page * 4;
        var end_byte = start_byte + galleries_per_page * 4 - 1;

        var xhr = new XMLHttpRequest();
        xhr.open('GET', nozomi_address);
        xhr.responseType = 'arraybuffer';
        xhr.setRequestHeader('Range', 'bytes='+start_byte.toString()+'-'+end_byte.toString());
        xhr.onreadystatechange = function(oEvent) {
                if (xhr.readyState === 4) {
                        if (xhr.status === 200 || xhr.status === 206) {
                                var arrayBuffer = xhr.response; // Note: not oReq.responseText
                                if (arrayBuffer) {
                                        var view = new DataView(arrayBuffer);
                                        var total = view.byteLength/4;
                                        for (var i = 0; i < total; i++) {
                                                nozomi.push(view.getInt32(i*4, false /* big-endian */));
                                        }
                                        total_items = parseInt(xhr.getResponseHeader("Content-Range").replace(/^[Bb]ytes \d+-\d+\//, '')) / 4;
                                        
                                        put_results_on_page();
                                }
                        }
                }
        };
        xhr.send();
}