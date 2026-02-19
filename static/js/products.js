

function showProductSkeleton() {
    const modal = document.getElementById("product-detail-modal");
    modal.querySelectorAll('.product_skeleton').forEach(el => el.classList.remove('hidden'));
    modal.querySelectorAll('.product-detail').forEach(el => el.classList.add('hidden'));
}

function hideProductSkeleton() {
    const modal = document.getElementById("product-detail-modal");
    modal.querySelectorAll('.product_skeleton').forEach(el => el.classList.add('hidden'));
    modal.querySelectorAll('.product-detail').forEach(el => el.classList.remove('hidden'));
}


function loadProduct(button) {
    const platformId = button.dataset.platformId;
    const modal = document.getElementById("product-detail-modal");
    const buy_product_btn = document.getElementById("buy-product-btn")
    showProductSkeleton();

    fetch(`${view_product_ajax}?platform_id=${platformId}`)
        .then(res => res.json())
        .then(response => {

            if (!response.data || !response.data.length) return;

            const item = response.data[0];
            const product = item.products[0];
            const productsListEl = document.getElementById("modal-products-list");
            productsListEl.innerHTML = "";

            item.products.forEach((p) => {
                const row = document.createElement("div");
                row.className = "flex items-center justify-between gap-3 rounded-lg border border-gray-200 bg-white p-2";
                row.innerHTML = `
                    <div class="flex items-center gap-2 min-w-0">
                        <img src="${p.product_image_url || default_image}" alt="${p.product_name}" class="h-12 w-12 rounded-md object-cover border border-gray-200">
                        <div class="min-w-0">
                            <div class="font-medium text-sm text-gray-800 truncate">${p.product_name}</div>
                            <div class="text-xs text-gray-500">Qty: ${p.quantity}x</div>
                        </div>
                    </div>
                    <div class="text-sm font-semibold text-gray-700">$${Number(p.line_total || 0).toFixed(2)}</div>
                `;
                productsListEl.appendChild(row);
            });

            document.getElementById("modal-category").innerText = item.product_type;
            document.getElementById("modal-order-date").innerText = item.order_datetime;
            document.getElementById("modal-product-image").src = item.platform_image || default_image;
            document.getElementById("modal-count").innerText = item.products_count + " Products";

            // document.getElementById("modal-brand").innerText = item.product_type;
            document.getElementById("modal-buy-price").innerText = "USDT " + Number(item.group_total || 0).toFixed(2);
            document.getElementById("modal-sell-price").innerText = "USDT " + Number((item.group_total || 0) + (item.group_profit || 0)).toFixed(2);
            document.getElementById("modal-expected-profit").innerText = "USDT " + Number(item.expected_profit || 0).toFixed(2);
            // document.getElementById("modal-profit").innerText = "USDT " + product.profit;

            // document.getElementById("modal-progress-percent").innerText = product.progress + "%";
            // document.getElementById("modal-progress-bar").style.width = product.progress + "%";


              const orderBtn = modal.querySelector('button[data-product-id]');
              orderBtn.setAttribute('data-product-id', "");
              orderBtn.setAttribute('data-group-id', item.group_id || "");
              hideProductSkeleton();
              
              if (item.disable_ordering) {
                disable_button(buy_product_btn)
              } else {enable_button(buy_product_btn)}
        })
        .catch(
            () => {
                hideProductSkeleton();
                alert("An error occurred while loading product data.");
            }
        );
}

function showComplitionModal() {
  const modalElement = document.getElementById("complition-popup-modal");
  const modal = new Modal(modalElement);
  modal.show();
}
function hideComplitionModal() {
  const modalElement = document.getElementById("complition-popup-modal");
  const modal = new Modal(modalElement);
  modal.hide();
}

function hideProductDetailModal() {
  const el = document.getElementById("product-detail-modal");
  el.click();
}

function disable_button(button) {
    button.disabled = true;
}
function enable_button(button) {
    button.disabled = false;
}

function buyProduct(order_button) {
    disable_button(order_button);
    showProductSkeleton();
    const modal = document.getElementById("product-detail-modal");
    const button = modal.querySelector('button[data-product-id]');
    const showProductBtn = document.getElementById("show-product-btn"); 
    const group_id = button.dataset.groupId || "";

    fetch(`${buy_product_ajax}?group_id=${group_id}`)
        .then(res => {
            if (!res.ok) {
                // Any status code other than 200-299
                throw new Error("Server connection error");
            }
            return res.json();
        })
        .then(response => {
            if (response.message) {
                tocastGen(response.message, response.status);
                if (response.is_done) {
                    hideProductDetailModal();
                    showComplitionModal();
                }
            }

            loadProduct(showProductBtn)
            hideProductSkeleton();
            enable_button(order_button);
        })
        .catch(error => {
            loadProduct(showProductBtn)
            tocastGen("An error occurred while purchasing the product.", 'error');
            hideProductSkeleton();
            enable_button(order_button);
        });
}




function showSkeleton() {
    const modal = document.getElementById("default-modal");
    modal.querySelectorAll('.product_skeleton').forEach(el => el.classList.remove('hidden'));
    modal.querySelector('#view-products-details').classList.add('hidden');
}

function hideSkeleton() {
    const modal = document.getElementById("default-modal");
    modal.querySelectorAll('.product_skeleton').forEach(el => el.classList.add('hidden'));
    modal.querySelector('#view-products-details').classList.remove('hidden');
}



function loadProducts(button) {
    const platformId = button.dataset.platformId;
    showSkeleton();
    fetch(`${view_products_ajax}?platform_id=${platformId}`)
        .then(res => res.json())
        .then(response => {
            const productsContainer = document.getElementById("view-products-details");
            const modal = document.getElementById("default-modal");
            

            productsContainer.innerHTML = ""; // Clear previous content
            if (!response.data) {
                modal.querySelector("#platform-name").innerText = "Error";
                modal.querySelector("#products-count").innerText = "0";
                hideSkeleton();
                return;
            }
            modal.querySelector("#platform-name").innerText = response.data.platform_name;
            modal.querySelector("#products-count").innerText = response.data.product_data.length + " Product";
            modal.querySelector("#platform-image").src = response.data.platform_image;

              
            if (!response.data.product_data.length) {
                hideSkeleton();
                productsContainer.innerHTML = "<p class='text-center text-gray-500'>No products to display.</p>";
                return;
            }

            for (const product of response.data.product_data) {
                if (product.status === 'locked') {
                    html = `

            <!-- Product with a gift -->
            <div class="relative p-4 rounded-xl border bg-gray-100 shadow-sm opacity-60">

              ${product.has_gift ? `
              <!-- Gift icon -->
              <div
                class="absolute -top-3 left-0 bg-pink-600 text-white w-8 h-8 rounded-full flex items-center justify-center shadow-lg">
                🎁
              </div>              
              ` : ``}


              <div class="flex items-center justify-between">
                <h3 class="text-lg font-bold text-gray-800">

                  Product ${product.stage}</h3>
                <span class="text-sm text-blue-600 font-semibold">Locked</span>
              </div>
              <p class="text-gray-600 mt-1 text-sm">${product.has_gift ? 'When you reach this product, you will get a gift.' : 'Complete the previous product to unlock it.'}</p>
            </div>

                    `


                } else if (product.status === 'current') {
                    

                    html = `

            <!-- Unlocked product -->
            <div class="relative p-4 rounded-xl border bg-white shadow-md border-green-500 border-4">

              <div class="flex items-center justify-between">
                <h3 class="text-lg font-bold text-gray-800 flex items-center gap-2">
                  <svg id='New_Product_32' width='32' height='32' viewBox='0 0 32 32' xmlns='http://www.w3.org/2000/svg'
                    xmlns:xlink='http://www.w3.org/1999/xlink'>
                    <rect width='32' height='32' stroke='none' fill='#000000' opacity='0' />
                    <g transform="matrix(0.44 0 0 0.44 16 16)">
                      <g style="">
                        <g transform="matrix(1 0 0 1 -5 4)">
                          <rect
                            style="stroke: none; stroke-width: 1; stroke-dasharray: none; stroke-linecap: butt; stroke-dashoffset: 0; stroke-linejoin: miter; stroke-miterlimit: 4; fill: rgb(239,216,190); fill-rule: nonzero; opacity: 1;"
                            x="-26" y="-21" rx="1" ry="1" width="52" height="42" />
                        </g>
                        <g transform="matrix(1 0 0 1 -5 22.5)">
                          <path
                            style="stroke: none; stroke-width: 1; stroke-dasharray: none; stroke-linecap: butt; stroke-dashoffset: 0; stroke-linejoin: miter; stroke-miterlimit: 4; fill: rgb(205,161,167); fill-rule: nonzero; opacity: 1;"
                            transform=" translate(-27, -54.5)"
                            d="M 5 52 L 49 52 C 51.20913899932317 52 53 53.79086100067683 53 56 L 53 57 L 1 57 L 1 56 C 1 53.79086100067683 2.790861000676826 52 5 52 Z"
                            stroke-linecap="round" />
                        </g>
                        <g transform="matrix(1 0 0 1 19.01 18.98)">
                          <path
                            style="stroke: none; stroke-width: 1; stroke-dasharray: none; stroke-linecap: butt; stroke-dashoffset: 0; stroke-linejoin: miter; stroke-miterlimit: 4; fill: rgb(114,202,175); fill-rule: nonzero; opacity: 1;"
                            transform=" translate(-51.01, -50.98)"
                            d="M 60.83 53.4 C 60.72654756381767 53.521396830674156 60.6858463589799 53.68420165002523 60.72 53.839999999999996 L 61.3 56.559999999999995 C 61.35296020725366 56.81204589268073 61.205797596979835 57.063087992559595 60.959999999999994 57.13999999999999 L 58.32 58 C 58.169256826786025 58.05091062339719 58.050910623397186 58.16925682678603 58 58.32 L 57.14 61 C 57.0630879925596 61.24579759697984 56.812045892680736 61.392960207253665 56.56 61.34 L 53.84 60.760000000000005 C 53.68420165002524 60.72584635897991 53.52139683067416 60.766547563817674 53.400000000000006 60.870000000000005 L 51.34 62.7 C 51.14969044963314 62.87175926792087 50.860309550366864 62.87175926792087 50.67 62.7 L 49.43 61.57 L 48.61 60.83 C 48.48860316932584 60.72654756381767 48.32579834997477 60.6858463589799 48.17 60.72 L 45.77 61.23 L 45.45 61.3 C 45.19795410731927 61.35296020725366 44.9469120074404 61.205797596979835 44.870000000000005 60.959999999999994 L 44 58.32 C 43.94908937660281 58.169256826786025 43.83074317321397 58.050910623397186 43.68 58 L 43.16 57.83 L 41 57.14 C 40.75420240302016 57.0630879925596 40.607039792746335 56.812045892680736 40.66 56.56 L 40.73 56.22 L 41.239999999999995 53.839999999999996 C 41.27415364102009 53.68420165002523 41.233452436182326 53.521396830674156 41.129999999999995 53.4 L 40 52 L 39.36 51.29 C 39.18824073207913 51.09969044963314 39.18824073207913 50.81030955036686 39.36 50.62 L 41.23 48.559999999999995 C 41.33345243618233 48.43860316932584 41.374153641020094 48.275798349974764 41.339999999999996 48.12 L 40.76 45.4 C 40.707039792746336 45.147954107319265 40.85420240302016 44.8969120074404 41.1 44.82 L 43.69 44 C 43.84074317321397 43.94908937660281 43.959089376602805 43.830743173213975 44.01 43.68 L 44.87 41 C 44.946912007440396 40.75420240302016 45.19795410731926 40.607039792746335 45.449999999999996 40.66 L 48.169999999999995 41.239999999999995 C 48.32579834997476 41.27415364102009 48.488603169325835 41.233452436182326 48.60999999999999 41.129999999999995 L 50.669999999999995 39.26 C 50.86030955036686 39.08824073207913 51.149690449633134 39.08824073207913 51.339999999999996 39.26 L 52 40 L 53.35 41.23 C 53.47139683067416 41.33345243618233 53.63420165002523 41.374153641020094 53.79 41.339999999999996 L 56.17 40.83 L 56.510000000000005 40.76 C 56.76204589268074 40.707039792746336 57.013087992559605 40.85420240302016 57.09 41.1 L 57.78 43.22 L 57.95 43.74 C 58.000910623397196 43.89074317321398 58.11925682678603 44.009089376602816 58.27 44.06 L 60.910000000000004 44.92 C 61.155797596979845 44.9969120074404 61.30296020725367 45.247954107319266 61.25000000000001 45.5 L 61.18000000000001 45.82 L 60.67000000000001 48.22 C 60.63584635897991 48.375798349974765 60.67654756381768 48.53860316932584 60.78000000000001 48.66 L 61.52000000000001 49.48 L 62.65000000000001 50.72 C 62.82175926792088 50.91030955036686 62.82175926792088 51.19969044963314 62.65000000000001 51.39 Z"
                            stroke-linecap="round" />
                        </g>
                        <g transform="matrix(1 0 0 1 -4.5 -20)">
                          <path
                            style="stroke: none; stroke-width: 1; stroke-dasharray: none; stroke-linecap: butt; stroke-dashoffset: 0; stroke-linejoin: miter; stroke-miterlimit: 4; fill: rgb(250,239,222); fill-rule: nonzero; opacity: 1;"
                            transform=" translate(-27.5, -12)" d="M 53 15 L 2 15 L 10 9 L 46 9 L 53 15 z"
                            stroke-linecap="round" />
                        </g>
                        <g transform="matrix(1 0 0 1 -6 2.03)">
                          <path
                            style="stroke: none; stroke-width: 1; stroke-dasharray: none; stroke-linecap: butt; stroke-dashoffset: 0; stroke-linejoin: miter; stroke-miterlimit: 4; fill: rgb(141,108,159); fill-rule: nonzero; opacity: 1;"
                            transform=" translate(-26, -34.03)"
                            d="M 10 50.06 C 9.447715250169207 50.06 9 50.507715250169205 9 51.06 L 9 53.06 C 9 53.6122847498308 9.447715250169207 54.06 10 54.06 C 10.552284749830793 54.06 11 53.6122847498308 11 53.06 L 11 51.06 C 11 50.507715250169205 10.552284749830793 50.06 10 50.06 z M 5 50.06 C 4.447715250169207 50.06 4 50.507715250169205 4 51.06 L 4 53.06 C 4 53.6122847498308 4.447715250169207 54.06 5 54.06 C 5.552284749830793 54.06 6 53.6122847498308 6 53.06 L 6 51.06 C 6 50.507715250169205 5.552284749830793 50.06 5 50.06 z M 15 50.06 C 14.447715250169207 50.06 14 50.507715250169205 14 51.06 L 14 53.06 C 14 53.6122847498308 14.447715250169207 54.06 15 54.06 C 15.552284749830793 54.06 16 53.6122847498308 16 53.06 L 16 51.06 C 16 50.507715250169205 15.552284749830793 50.06 15 50.06 z M 20 50.06 C 19.447715250169207 50.06 19 50.507715250169205 19 51.06 L 19 53.06 C 19 53.6122847498308 19.447715250169207 54.06 20 54.06 C 20.552284749830793 54.06 21 53.6122847498308 21 53.06 L 21 51.06 C 21 50.507715250169205 20.552284749830793 50.06 20 50.06 z M 25 50.06 C 24.447715250169207 50.06 24 50.507715250169205 24 51.06 L 24 53.06 C 24 53.6122847498308 24.447715250169207 54.06 25 54.06 C 25.552284749830793 54.06 26 53.6122847498308 26 53.06 L 26 51.06 C 26 50.507715250169205 25.552284749830793 50.06 25 50.06 z M 30 50.06 C 29.447715250169207 50.06 29 50.507715250169205 29 51.06 L 29 53.06 C 29 53.6122847498308 29.447715250169207 54.06 30 54.06 C 30.552284749830793 54.06 31 53.6122847498308 31 53.06 L 31 51.06 C 31 50.507715250169205 30.552284749830793 50.06 30 50.06 z M 35 50.06 C 34.4477152501692 50.06 34 50.507715250169205 34 51.06 L 34 53.06 C 34 53.6122847498308 34.4477152501692 54.06 35 54.06 C 35.5522847498308 54.06 36 53.6122847498308 36 53.06 L 36 51.06 C 36 50.507715250169205 35.5522847498308 50.06 35 50.06 z M 43 16 L 47 16 C 47.5522847498308 16 48 15.552284749830793 48 15 C 48 14.447715250169207 47.5522847498308 14 47 14 L 43 14 C 42.4477152501692 14 42 14.447715250169207 42 15 C 42 15.552284749830793 42.4477152501692 16 43 16 z M 37 40 L 17 40 C 16.447715250169207 40 16 40.4477152501692 16 41 C 16 41.5522847498308 16.447715250169207 42 17 42 L 37 42 C 37.5522847498308 42 38 41.5522847498308 38 41 C 38 40.4477152501692 37.5522847498308 40 37 40 z M 23 22 L 31 22 C 31.552284749830793 22 32 21.552284749830793 32 21 C 32 20.447715250169207 31.552284749830793 20 31 20 L 23 20 C 22.447715250169207 20 22 20.447715250169207 22 21 C 22 21.552284749830793 22.447715250169207 22 23 22 z M 18.71 30.71 L 20 29.41 L 20 37 C 20 37.5522847498308 20.447715250169207 38 21 38 C 21.552284749830793 38 22 37.5522847498308 22 37 L 22 29.41 L 23.29 30.7 C 23.6867602774557 31.039776795928702 24.278194171545707 31.016932269681032 24.647563220613367 30.647563220613367 C 25.016932269681032 30.278194171545707 25.039776795928702 29.6867602774557 24.7 29.29 L 21.7 26.29 C 21.309962545689075 25.9022764052892 20.680037454310924 25.9022764052892 20.29 26.29 L 17.29 29.29 C 16.950223204071296 29.6867602774557 16.973067730318967 30.278194171545707 17.34243677938663 30.647563220613367 C 17.711805828454292 31.016932269681032 18.303239722544298 31.039776795928702 18.7 30.7 z M 29.29 30.71 C 29.680037454310924 31.0977235947108 30.309962545689075 31.0977235947108 30.7 30.71 L 32 29.41 L 32 37 C 32 37.5522847498308 32.4477152501692 38 33 38 C 33.5522847498308 38 34 37.5522847498308 34 37 L 34 29.41 L 35.29 30.7 C 35.686760277455704 31.03977679592869 36.2781941715457 31.016932269681014 36.64756322061336 30.647563220613357 C 37.016932269681014 30.278194171545696 37.03977679592869 29.6867602774557 36.699999999999996 29.29 L 33.699999999999996 26.29 C 33.309962545689075 25.902276405289204 32.68003745431092 25.902276405289204 32.29 26.29 L 29.29 29.29 C 29.1006873491769 29.477766599905554 28.994201675658328 29.73336246362944 28.994201675658328 30 C 28.994201675658328 30.26663753637056 29.1006873491769 30.522233400094443 29.29 30.71 z"
                            stroke-linecap="round" />
                        </g>
                        <g transform="matrix(1 0 0 1 -0.09 3.91)">
                          <path
                            style="stroke: none; stroke-width: 1; stroke-dasharray: none; stroke-linecap: butt; stroke-dashoffset: 0; stroke-linejoin: miter; stroke-miterlimit: 4; fill: rgb(141,108,159); fill-rule: nonzero; opacity: 1;"
                            transform=" translate(-31.91, -35.91)"
                            d="M 63.44 50 L 61.75 48.13 L 62.28 45.660000000000004 C 62.44088266745389 44.909583268254195 62.00938125012537 44.15877080210256 61.28 43.92 L 58.88 43.14 L 58.1 40.74 C 57.865103473446055 40.00747771164037 57.111180296139715 39.5741885292804 56.36 39.74 L 54.01 40.24 L 54.01 17 C 54.01 15.426213483334735 53.26902921333221 13.94427190999916 52.01 13 L 46.67 9 C 45.80218637962787 8.355354079233226 44.751038448757775 8.00497143560986 43.67 8 L 10.33 8 C 9.248961551242228 8.004971435609862 8.19781362037213 8.355354079233228 7.329999999999998 9.000000000000002 L 2 13 C 0.7409707866677884 13.94427190999916 0 15.426213483334735 0 17 L 0 55 C 0 56.65685424949238 1.3431457505076196 58 3 58 L 40.51 58 L 40.739999999999995 58.09 L 43.13999999999999 58.870000000000005 L 43.919999999999995 61.27 C 44.15877080210255 61.999381250125374 44.90958326825419 62.43088266745389 45.66 62.27 L 48.129999999999995 61.74 L 50 63.44 C 50.27432057095757 63.688083285418365 50.63015243924898 63.82685771405202 51 63.83 C 51.370391351033184 63.82971223941777 51.72721180470864 63.690552262484346 52 63.44 L 53.87 61.75 L 56.339999999999996 62.28 C 57.090416731745805 62.44088266745389 57.84122919789744 62.00938125012537 58.08 61.28 L 58.86 58.88 L 61.26 58.1 C 61.99252228835963 57.865103473446055 62.4258114707196 57.111180296139715 62.26 56.36 L 61.73 53.89 L 63.44 52 C 63.953891508447775 51.43236501425386 63.953891508447775 50.56763498574614 63.44 50 Z M 8.53 10.6 C 9.049288512538814 10.210533615595889 9.680889359326482 10 10.329999999999998 10 L 26 10 L 26 14 L 4 14 Z M 2 55 L 2 16 L 39 16 C 39.5522847498308 16 40 15.552284749830793 40 15 C 40 14.447715250169207 39.5522847498308 14 39 14 L 28 14 L 28 10 L 43.67 10 C 44.31911064067352 10 44.950711487461184 10.210533615595889 45.47 10.6 L 50.8 14.6 C 51.555417527999325 15.166563145999493 52 16.05572809000084 52 17 L 52 38.56 C 51.43236501425386 38.046108491552225 50.56763498574614 38.046108491552225 50 38.56 L 48.13 40.25 L 45.660000000000004 39.72 C 44.90881970386029 39.554188529280395 44.15489652655395 39.987477711640366 43.92 40.72 L 43.14 43.12 L 40.74 43.9 C 40.01061874987463 44.138770802102556 39.57911733254611 44.88958326825419 39.74 45.64 L 40.27 48.11 L 38.57 50 C 38.05610849155222 50.56763498574614 38.05610849155222 51.43236501425386 38.57 52 L 40.26 53.87 L 39.81 56 L 3 56 C 2.4477152501692068 56 2 55.5522847498308 2 55 Z M 60.09 52.73 C 59.785087830433184 53.077442923341174 59.656120583916056 53.54540978927476 59.74 54 L 60.230000000000004 56.28 L 58 57 C 57.521527347543966 57.14698831429282 57.14698831429282 57.521527347543966 57 58 L 56.29 60.22 L 54 59.74 C 53.529366322973864 59.63967236776748 53.03909526582218 59.769668481406185 52.68 60.09 L 51 61.65 L 49.28 60.089999999999996 C 49.00420772399636 59.84554543187662 48.648536650753655 59.71039042404439 48.28 59.709999999999994 C 48.17690132656581 59.70015150984599 48.07309867343419 59.70015150984599 47.97 59.709999999999994 L 45.69 60.199999999999996 L 45 58 L 45 58 C 44.84416760454907 57.5269103022359 44.4730896977641 57.15583239545093 44 57 L 41.78 56.29 L 41.85 55.96 L 42.27 54.02 C 42.37038646809892 53.54625945576938 42.2405713903758 53.052962160421494 41.92 52.690000000000005 L 40.36 51 L 41.92 49.28 C 42.22658429694489 48.92947540349582 42.355570502169925 48.45775442438713 42.27 48 L 41.78 45.72 L 44 45 C 44.48133082697009 44.8577903500731 44.8577903500731 44.48133082697009 45 44 L 45.72 41.78 L 47.99 42.27 C 48.463740544230625 42.37038646809892 48.95703783957851 42.2405713903758 49.32 41.92 L 51 40.36 L 52 41.26 L 52.73 41.919999999999995 C 53.075211408665155 42.22902554185103 53.54521909059576 42.35855521797364 54 42.269999999999996 C 54 42.269999999999996 54 42.269999999999996 54 42.269999999999996 L 56.28 41.779999999999994 L 57 44 C 57.1422096499269 44.48133082697009 57.51866917302991 44.8577903500731 58 45 L 60.22 45.72 L 59.74 48 C 59.63967236776748 48.470633677026136 59.769668481406185 48.96090473417782 60.09 49.32 L 61.65 51 Z"
                            stroke-linecap="round" />
                        </g>
                      </g>
                    </g>
                  </svg>

                  ${product.product_name}
                </h3>
                <span class="text-sm text-green-600 font-semibold">Available</span>
              </div>
              <p class="text-gray-600 mt-1 text-sm">You can start selling this product now.</p>
            </div>
                    `

                  
                } else if (product.status === 'completed') {
                    

                    html = `

            <!-- Completed product -->
            <div class="relative p-4 rounded-xl border bg-white">

              <div class="flex items-center justify-between">
                <h3 class="text-lg font-bold text-gray-800 flex items-center gap-2">

                  <svg id='Used_Product_32' width='32' height='32' viewBox='0 0 32 32'
                    xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'>
                    <rect width='32' height='32' stroke='none' fill='#000000' opacity='0' />
                    <g transform="matrix(0.58 0 0 0.58 16 16)">
                      <g style="">
                        <g transform="matrix(1 0 0 1 -5.71 4.35)">
                          <path
                            style="stroke: none; stroke-width: 1; stroke-dasharray: none; stroke-linecap: butt; stroke-dashoffset: 0; stroke-linejoin: miter; stroke-miterlimit: 4; fill: rgb(197,101,40); fill-rule: nonzero; opacity: 1;"
                            transform=" translate(-18.29, -28.35)"
                            d="M 4.488 13.284 C 4.488 13.284 9.198 15.393 14.484000000000002 16.634 C 19.770000000000003 17.875 22.977000000000004 18.593 24.771 18.286 C 26.565 17.979000000000003 31.177 16.658 33.224000000000004 17.183 C 32.604000000000006 18.562 31.762000000000004 22.442999999999998 30.601000000000003 24.738 C 29.44 27.033 28.948000000000004 28.522 30.186000000000003 32.125 C 31.424000000000003 35.728 32.563 39.521 31.583000000000002 42.812 C 28.912000000000003 43.143 25.528000000000002 43.907 21.805 42.964 C 18.083 42.019999999999996 17.195 41.702999999999996 12.326 41.195 C 7.458 40.687 5.166 40.146 5.166 40.146 C 5.166 40.146 5.19 34.699 3.9700000000000006 32.673 C 2.750000000000001 30.647000000000006 3.625 27.5 4.271 25.125 C 4.917 22.75 4.488 13.284 4.488 13.284 z"
                            stroke-linecap="round" />
                        </g>
                        <g transform="matrix(1 0 0 1 12.89 1.12)">
                          <path
                            style="stroke: none; stroke-width: 1; stroke-dasharray: none; stroke-linecap: butt; stroke-dashoffset: 0; stroke-linejoin: miter; stroke-miterlimit: 4; fill: rgb(197,101,40); fill-rule: nonzero; opacity: 1;"
                            transform=" translate(-36.89, -25.12)"
                            d="M 31.984 42.469 L 34.495000000000005 40.434 C 34.495000000000005 40.434 35.344 39.919 36.724000000000004 38.866 C 38.319 37.649 40.92100000000001 34.775 41.64 33.497 C 41.281 31.938 41.671 29.6 41.56 27.064 C 41.449000000000005 24.529 41.396 22.063 42.047000000000004 19.589 C 42.69800000000001 17.115 44.42100000000001 7.889999999999999 44.42100000000001 7.889999999999999 C 44.42100000000001 7.889999999999999 43.91700000000001 7.254999999999999 42.263000000000005 8.806999999999999 C 40.609 10.358999999999998 37.742000000000004 11.916999999999998 37.196000000000005 12.602999999999998 C 36.650000000000006 13.288999999999998 33.234 16.554 32.73400000000001 18.124 C 32.234000000000016 19.694 31.66500000000001 22.552999999999997 30.84500000000001 24.235 C 30.02500000000001 25.916999999999998 28.66900000000001 27.817999999999998 29.75300000000001 30.904 C 30.83700000000001 33.99 32.333 37.738 31.984 42.469 z"
                            stroke-linecap="round" />
                        </g>
                        <g transform="matrix(1 0 0 1 0.04 -11.93)">
                          <path
                            style="stroke: none; stroke-width: 1; stroke-dasharray: none; stroke-linecap: butt; stroke-dashoffset: 0; stroke-linejoin: miter; stroke-miterlimit: 4; fill: rgb(245,132,32); fill-rule: nonzero; opacity: 1;"
                            transform=" translate(-24.04, -12.07)"
                            d="M 4.313 13.024 C 4.313 13.024 8.373 15.341 15.405000000000001 16.874 C 22.437000000000005 18.406999999999996 23.972 18.596 26.85 17.898 C 29.728 17.198999999999998 32.741 16.980999999999998 33.388000000000005 17.014 C 34.07000000000001 15.988999999999999 36.993 12.616 39.318000000000005 10.988 C 41.64300000000001 9.36 42.795 8.129 43.772000000000006 7.9079999999999995 C 43.772000000000006 6.145999999999999 36.94800000000001 6.859 32.37100000000001 5.859 C 30.79000000000001 5.881 30.93900000000001 7.399 29.42100000000001 7.375 C 28.04600000000001 7.354 26.73800000000001 7.244 25.56900000000001 6.919 C 23.10900000000001 6.234 21.518000000000008 5.609999999999999 20.09900000000001 6.154999999999999 C 18.680000000000014 6.699999999999999 4.797 12.156 4.313 13.024 z"
                            stroke-linecap="round" />
                        </g>
                        <g transform="matrix(1 0 0 1 0.37 -7.4)">
                          <polygon
                            style="stroke: none; stroke-width: 1; stroke-dasharray: none; stroke-linecap: butt; stroke-dashoffset: 0; stroke-linejoin: miter; stroke-miterlimit: 4; fill: rgb(81,54,32); fill-rule: nonzero; opacity: 1;"
                            points="-7.09,0.63 -4.01,-1.77 7.09,0.85 1.31,1.77 " />
                        </g>
                        <g transform="matrix(1 0 0 1 -7.13 -1.89)">
                          <path
                            style="stroke: none; stroke-width: 1; stroke-dasharray: none; stroke-linecap: butt; stroke-dashoffset: 0; stroke-linejoin: miter; stroke-miterlimit: 4; fill: rgb(81,54,32); fill-rule: nonzero; opacity: 1;"
                            transform=" translate(-16.87, -22.11)"
                            d="M 17.583 20.854 C 15.936999999999998 20.333 15.203999999999999 20.516 12.857 20.078 C 12.76 20.06 12.658 20.043 12.565 20.076999999999998 C 12.404 20.136 12.334 20.323999999999998 12.312999999999999 20.494 C 12.232999999999999 21.126 12.557999999999998 21.758 13.028999999999998 22.187 C 13.498999999999999 22.617 14.098999999999998 22.875 14.696999999999997 23.093 C 16.660999999999998 23.808 18.751999999999995 24.173000000000002 20.842 24.163 C 20.956999999999997 24.162 21.076 24.16 21.18 24.111 C 21.381 24.017 21.473 23.766000000000002 21.44 23.547 C 21.407 23.327 21.273 23.136 21.123 22.972 C 20.476 22.264 18.497 21.143 17.583 20.854 z"
                            stroke-linecap="round" />
                        </g>
                        <g transform="matrix(1 0 0 1 -7.13 -1.89)">
                          <path
                            style="stroke: none; stroke-width: 1; stroke-dasharray: none; stroke-linecap: butt; stroke-dashoffset: 0; stroke-linejoin: miter; stroke-miterlimit: 4; fill: rgb(1,1,1); fill-rule: nonzero; opacity: 1;"
                            transform=" translate(-16.87, -22.11)"
                            d="M 20.768 24.663 C 18.631 24.663 16.533 24.293 14.526 23.562 C 13.894 23.333000000000002 13.234 23.051000000000002 12.692 22.555 C 12.05 21.968 11.723 21.174 11.817 20.43 C 11.870000000000001 20.022 12.08 19.722 12.392 19.607 C 12.618 19.523 12.834 19.564 12.952 19.586 C 13.931 19.769 14.62 19.840999999999998 15.228 19.904 C 16.073999999999998 19.993 16.743 20.062 17.735 20.377 L 17.735 20.377 C 18.656 20.668 20.749 21.819 21.492 22.634 C 21.746000000000002 22.912 21.891000000000002 23.186 21.934 23.472 C 22.005000000000003 23.932000000000002 21.782 24.382 21.392 24.564 C 21.148 24.679 20.93 24.664 20.768 24.663 z M 12.818 20.579 C 12.786 21.037 12.997 21.479 13.366 21.817 C 13.78 22.196 14.331999999999999 22.427 14.866999999999999 22.623 C 16.787 23.322000000000003 18.784 23.642 20.839 23.663 C 20.877 23.663 20.950999999999997 23.662 20.974999999999998 23.655 C 20.932 23.540000000000003 20.868 23.434 20.752999999999997 23.308 C 20.189999999999998 22.692 18.293999999999997 21.603 17.432999999999996 21.33 L 17.432999999999996 21.33 C 16.536999999999995 21.046999999999997 15.944999999999997 20.983999999999998 15.123999999999995 20.898999999999997 C 14.508 20.836 13.811 20.763 12.818 20.579 z"
                            stroke-linecap="round" />
                        </g>
                        <g transform="matrix(1 0 0 1 -6.08 14.59)">
                          <path
                            style="stroke: none; stroke-width: 1; stroke-dasharray: none; stroke-linecap: butt; stroke-dashoffset: 0; stroke-linejoin: miter; stroke-miterlimit: 4; fill: rgb(1,1,1); fill-rule: nonzero; opacity: 1;"
                            transform=" translate(-17.92, -38.59)"
                            d="M 22.251 39.935 C 21.384 39.935 20.547 39.699000000000005 19.731 39.468 C 19.507 39.405 19.284000000000002 39.342000000000006 19.062 39.284000000000006 C 18.137 39.044000000000004 17.174 38.894000000000005 16.243000000000002 38.75000000000001 L 12.925000000000002 38.232000000000006 C 12.652000000000003 38.18900000000001 12.466000000000003 37.93300000000001 12.508000000000003 37.66100000000001 C 12.551000000000002 37.38900000000001 12.809000000000003 37.20400000000001 13.079000000000002 37.24400000000001 L 16.396 37.76200000000001 C 17.351 37.91000000000001 18.338 38.06400000000001 19.312 38.31600000000001 C 19.541 38.37600000000001 19.772000000000002 38.44100000000001 20.003 38.50600000000001 C 20.961 38.77600000000001 21.864 39.031000000000006 22.755 38.89900000000001 C 23.029 38.85500000000001 23.282 39.04500000000001 23.323999999999998 39.31900000000001 C 23.365 39.59100000000001 23.177 39.84600000000001 22.903999999999996 39.88700000000001 C 22.685 39.92 22.467 39.935 22.251 39.935 z"
                            stroke-linecap="round" />
                        </g>
                        <g transform="matrix(1 0 0 1 -9.52 9.07)">
                          <path
                            style="stroke: none; stroke-width: 1; stroke-dasharray: none; stroke-linecap: butt; stroke-dashoffset: 0; stroke-linejoin: miter; stroke-miterlimit: 4; fill: rgb(1,1,1); fill-rule: nonzero; opacity: 1;"
                            transform=" translate(-14.48, -33.07)"
                            d="M 15.857 32.458 L 14.847999999999999 30.325999999999997 C 14.761 30.141 14.578 30.013999999999996 14.367999999999999 30.040999999999997 C 14.165 30.052999999999997 13.988999999999999 30.185999999999996 13.922999999999998 30.378999999999998 C 13.734999999999998 30.929999999999996 13.473999999999998 31.453999999999997 13.148999999999997 31.938 C 12.994999999999997 32.167 13.055999999999997 32.478 13.284999999999997 32.632 C 13.513999999999996 32.786 13.824999999999996 32.726 13.978999999999996 32.495999999999995 C 14.013999999999996 32.443 14.041999999999996 32.385999999999996 14.075999999999995 32.331999999999994 C 14.049999999999995 33.010999999999996 14.070999999999994 33.62599999999999 14.148999999999996 34.205999999999996 L 14.170999999999996 34.367999999999995 C 14.226999999999995 34.757999999999996 14.278999999999996 35.126999999999995 14.159999999999997 35.400999999999996 C 14.050999999999997 35.654999999999994 14.166999999999996 35.949 14.419999999999996 36.059 C 14.484999999999996 36.086999999999996 14.551999999999996 36.099999999999994 14.617999999999997 36.099999999999994 C 14.810999999999996 36.099999999999994 14.994999999999997 35.98799999999999 15.076999999999996 35.79899999999999 C 15.307999999999996 35.263999999999996 15.229999999999997 34.712999999999994 15.159999999999997 34.22599999999999 L 15.138999999999996 34.07299999999999 C 15.093999999999996 33.73799999999999 15.071999999999996 33.38499999999999 15.065999999999995 33.013999999999996 C 15.159999999999995 33.105999999999995 15.273999999999996 33.172 15.403999999999995 33.172 C 15.474999999999994 33.172 15.548999999999994 33.156 15.616999999999994 33.123999999999995 C 15.868 33.006 15.975 32.708 15.857 32.458 z"
                            stroke-linecap="round" />
                        </g>
                        <g transform="matrix(1 0 0 1 -3.92 10.05)">
                          <path
                            style="stroke: none; stroke-width: 1; stroke-dasharray: none; stroke-linecap: butt; stroke-dashoffset: 0; stroke-linejoin: miter; stroke-miterlimit: 4; fill: rgb(1,1,1); fill-rule: nonzero; opacity: 1;"
                            transform=" translate(-20.08, -34.05)"
                            d="M 20.482 31.583 C 20.477 31.372999999999998 20.341 31.189 20.143 31.122 C 19.943 31.056 19.725 31.118 19.593 31.281 C 19.18 31.793 18.83 32.354 18.554 32.949 C 18.448999999999998 33.178 18.528 33.448 18.74 33.583 C 18.951999999999998 33.717 19.232 33.672 19.392 33.48 C 19.438 33.424 19.483 33.369 19.527 33.312 L 19.61 36.510999999999996 C 19.617 36.782 19.839 36.998 20.11 36.998 C 20.114 36.998 20.119 36.998 20.124 36.998 C 20.4 36.989999999999995 20.618 36.760999999999996 20.610999999999997 36.485 L 20.545999999999996 33.957 C 20.695999999999994 34.139 20.952999999999996 34.274 21.216999999999995 34.219 C 21.431999999999995 34.173 21.633999999999997 33.938 21.651999999999994 33.718 C 21.671 33.461 20.482 31.583 20.482 31.583 z"
                            stroke-linecap="round" />
                        </g>
                        <g transform="matrix(1 0 0 1 -0.15 0.57)">
                          <path
                            style="stroke: none; stroke-width: 1; stroke-dasharray: none; stroke-linecap: butt; stroke-dashoffset: 0; stroke-linejoin: miter; stroke-miterlimit: 4; fill: rgb(1,1,1); fill-rule: nonzero; opacity: 1;"
                            transform=" translate(-23.85, -24.57)"
                            d="M 42.271 20.623 C 43.522 16.368000000000002 44.379 12.165000000000001 44.891 7.772 C 44.908 7.6240000000000006 44.856 7.487 44.763999999999996 7.384 C 44.763 7.383 44.76199999999999 7.383 44.76199999999999 7.382000000000001 C 44.721999999999994 7.337000000000001 44.67499999999999 7.300000000000001 44.620999999999995 7.272 C 44.61599999999999 7.269 44.61299999999999 7.264 44.60699999999999 7.261 C 44.55799999999999 7.237 44.50899999999999 7.213 44.459999999999994 7.189 C 44.382999999999996 7.111 44.285999999999994 7.063 44.175999999999995 7.05 C 43.629999999999995 6.788 43.062 6.554 42.431999999999995 6.486 C 41.535999999999994 6.388999999999999 40.696999999999996 6.364 39.885 6.34 C 38.661 6.303 37.605 6.272 36.707 6.004 C 36.154 5.84 34.779 5.669 33.673 5.532 C 33.243 5.479 32.763000000000005 5.42 32.565000000000005 5.386 C 32.55200000000001 5.377 32.535000000000004 5.376 32.52100000000001 5.368 C 32.476000000000006 5.3420000000000005 32.43000000000001 5.322 32.379000000000005 5.311 C 32.354000000000006 5.305 32.331 5.303 32.30500000000001 5.301 C 32.254000000000005 5.298 32.20300000000001 5.304 32.15200000000001 5.3180000000000005 C 32.135000000000005 5.322 32.11700000000001 5.317 32.10000000000001 5.324000000000001 C 32.09100000000001 5.327000000000001 32.08500000000001 5.335000000000001 32.07600000000001 5.339 C 32.068000000000005 5.343 32.059000000000005 5.3420000000000005 32.05100000000001 5.346 C 31.085000000000008 5.827 30.21100000000001 6.244 29.393000000000008 6.634 C 29.34200000000001 6.658 29.294000000000008 6.681 29.244000000000007 6.705 C 26.737000000000005 6.737 24.570000000000007 6.052 22.139000000000006 5.621 C 20.220000000000006 5.28 18.666000000000007 6.1690000000000005 16.893000000000008 6.859 C 12.386000000000008 8.614 7.890000000000008 10.415 3.5490000000000084 12.555 C 3.2350000000000083 12.709999999999999 3.2090000000000085 13.272 3.5490000000000084 13.419 C 3.6180000000000083 13.449 3.6880000000000086 13.477 3.7570000000000086 13.507 C 4.3020000000000085 14.706 4.160000000000009 16.669 4.058000000000009 18.002 C 4.016000000000009 18.551 3.9830000000000085 18.983999999999998 4.002000000000009 19.281 C 4.195000000000008 22.267 4.254000000000008 23.837 3.5060000000000087 26.848999999999997 C 3.4390000000000085 27.119999999999997 3.3610000000000086 27.391 3.2840000000000087 27.661999999999995 C 3.0750000000000086 28.395999999999994 2.859000000000009 29.154999999999994 2.8220000000000085 29.956999999999994 C 2.7480000000000087 31.550999999999995 2.8220000000000085 31.791999999999994 3.3170000000000086 32.56799999999999 C 3.4760000000000084 32.81799999999999 3.6880000000000086 33.148999999999994 3.9620000000000086 33.68299999999999 C 4.420000000000009 34.574999999999996 4.510000000000009 36.24999999999999 4.588000000000009 37.72899999999999 C 4.642000000000009 38.74499999999999 4.693000000000009 39.70399999999999 4.853000000000009 40.42699999999999 C 4.899000000000009 40.63799999999999 5.0760000000000085 40.794999999999995 5.290000000000009 40.81699999999999 C 6.945000000000009 40.98799999999999 9.224000000000009 41.288999999999994 11.427000000000008 41.57999999999999 C 13.65000000000001 41.87299999999999 15.948000000000008 42.17699999999999 17.631000000000007 42.349999999999994 C 18.188000000000006 42.407999999999994 18.714000000000006 42.461999999999996 19.215000000000007 42.605999999999995 C 19.516000000000005 42.690999999999995 19.807000000000006 42.80799999999999 20.098000000000006 42.92399999999999 C 20.261000000000006 42.98799999999999 20.423000000000005 43.053999999999995 20.587000000000007 43.11399999999999 C 22.109000000000005 43.67299999999999 23.716000000000008 43.83699999999999 25.296000000000006 43.83699999999999 C 26.484000000000005 43.83699999999999 27.65500000000001 43.743999999999986 28.764000000000006 43.65599999999999 C 29.285000000000007 43.614999999999995 29.827000000000005 43.55299999999999 30.369000000000007 43.49199999999999 C 30.878000000000007 43.43399999999999 31.387000000000008 43.37699999999999 31.877000000000006 43.33699999999999 C 31.917000000000005 43.33599999999999 31.959000000000007 43.33199999999999 32.00000000000001 43.322999999999986 C 32.21000000000001 43.28199999999999 32.358000000000004 43.11199999999999 32.39000000000001 42.90999999999999 C 33.41000000000001 41.88899999999999 36.36900000000001 39.578999999999986 36.757000000000005 39.38599999999999 C 38.668000000000006 38.673999999999985 39.77700000000001 36.97299999999999 40.85000000000001 35.325999999999986 C 41.19000000000001 34.804999999999986 41.53000000000001 34.28199999999999 41.89500000000001 33.79499999999999 C 42.04800000000001 33.58999999999999 42.01400000000001 33.31199999999999 41.83400000000001 33.139999999999986 C 41.51600000000001 31.250999999999987 41.63900000000001 29.349999999999987 41.78600000000001 27.342999999999986 C 41.88600000000001 25.981999999999985 41.99000000000001 24.573999999999984 41.93400000000001 23.168999999999986 C 41.91700000000001 22.746999999999986 41.902000000000015 22.348999999999986 41.948000000000015 21.960999999999988 C 42 21.543 42.122 21.128 42.271 20.623 z M 36.419 6.964 C 37.442 7.269 38.613 7.303000000000001 39.852999999999994 7.340000000000001 C 40.645999999999994 7.363 41.464999999999996 7.388000000000001 42.32299999999999 7.481000000000001 C 42.49399999999999 7.500000000000001 42.66499999999999 7.539000000000001 42.834999999999994 7.590000000000001 C 42.57899999999999 7.791 42.34499999999999 8.017000000000001 42.12799999999999 8.237 L 41.913999999999994 8.452 C 41.23799999999999 9.114 40.449999999999996 9.637 39.61599999999999 10.189 C 39.33699999999999 10.374 39.05799999999999 10.558 38.78399999999999 10.748 C 36.50599999999999 12.328999999999999 34.54299999999999 14.277999999999999 32.94099999999999 16.535 C 32.89999999999999 16.526 32.86199999999999 16.513 32.81599999999999 16.514 C 31.12799999999999 16.56 29.398999999999987 16.392 27.81199999999999 16.041999999999998 L 27.24599999999999 15.911999999999997 C 26.455999999999992 15.728999999999997 25.261999999999993 15.451999999999996 23.68399999999999 15.163999999999998 C 23.22399999999999 15.079999999999998 21.97999999999999 14.727999999999998 20.77699999999999 14.388999999999998 C 19.99499999999999 14.167999999999997 19.24199999999999 13.954999999999998 18.65699999999999 13.800999999999998 C 19.15099999999999 13.479 19.88899999999999 13.149999999999999 20.44499999999999 12.903999999999998 C 21.12499999999999 12.602999999999998 21.71299999999999 12.342999999999998 22.07599999999999 12.064999999999998 C 24.94999999999999 9.858999999999998 27.09899999999999 8.834999999999997 29.82199999999999 7.537999999999998 C 30.579999999999988 7.176999999999998 31.39499999999999 6.786999999999997 32.27699999999999 6.3489999999999975 C 32.444999999999986 6.388999999999998 32.81599999999999 6.435999999999997 33.54799999999999 6.5269999999999975 C 34.503 6.645 35.947 6.823 36.419 6.964 z M 20.38 15.315 C 20.422 15.327 20.462999999999997 15.338 20.505 15.35 C 21.787 15.712 22.997999999999998 16.055 23.505 16.148 C 25.06 16.431 26.24 16.705 27.021 16.886 L 27.598 17.018 C 28.119 17.133 28.657 17.222 29.201 17.298000000000002 C 28.705000000000002 17.372000000000003 28.204 17.458000000000002 27.684 17.572000000000003 C 25.936 17.953000000000003 24.165 18.283 22.39 17.880000000000003 C 21.404 17.656000000000002 20.51 17.267000000000003 19.505000000000003 17.111000000000004 C 19.110000000000003 17.050000000000004 18.718000000000004 16.976000000000003 18.325000000000003 16.907000000000004 C 18.598000000000003 16.701000000000004 18.873000000000005 16.496000000000002 19.148000000000003 16.292000000000005 C 19.415000000000003 16.094000000000005 19.704000000000004 15.916000000000006 19.963000000000005 15.708000000000006 C 20.1 15.596 20.231 15.418 20.38 15.315 z M 17.157 7.824 C 18.042 7.479 18.969 6.989 19.89 6.765 C 21.32 6.4159999999999995 22.533 6.7669999999999995 23.915 7.098 C 25.061999999999998 7.373 26.180999999999997 7.548 27.319 7.638 C 25.423 8.584 23.654 9.592 21.466 11.271 C 21.198 11.476 20.609 11.737 20.040000000000003 11.989 C 18.869000000000003 12.507000000000001 17.668000000000003 13.044 17.276000000000003 13.803 C 17.271000000000004 13.81 17.268000000000004 13.818000000000001 17.263 13.825000000000001 C 17.253 13.846000000000002 17.236 13.866000000000001 17.227 13.887 C 17.219 13.905000000000001 17.221 13.925 17.215 13.944 C 17.21 13.961 17.199 13.975000000000001 17.195 13.993 C 17.192 14.008000000000001 17.197 14.022 17.196 14.036 C 17.193 14.071 17.194000000000003 14.104 17.198 14.139 C 17.202 14.17 17.206 14.2 17.216 14.229999999999999 C 17.226000000000003 14.259999999999998 17.238 14.287999999999998 17.253 14.315999999999999 C 17.269 14.344999999999999 17.285 14.371999999999998 17.306 14.396999999999998 C 17.325 14.419999999999998 17.347 14.439999999999998 17.37 14.459999999999999 C 17.397000000000002 14.482999999999999 17.425 14.501999999999999 17.457 14.518999999999998 C 17.470000000000002 14.525999999999998 17.478 14.536999999999999 17.492 14.542999999999997 C 17.509 14.549999999999997 17.526 14.547999999999998 17.543 14.552999999999997 C 17.561999999999998 14.558999999999997 17.576999999999998 14.570999999999998 17.596999999999998 14.574999999999998 C 17.892999999999997 14.628999999999998 18.514 14.793999999999997 19.238 14.994999999999997 C 19.043 15.143999999999997 18.837 15.282999999999998 18.642 15.427999999999997 C 18.092 15.835999999999997 17.549 16.252999999999997 16.996 16.657999999999998 C 12.892 15.832999999999998 8.902999999999999 14.570999999999998 5.024999999999999 12.960999999999999 C 8.988 11.063 13.064 9.418 17.157 7.824 z M 31.212 42.396 C 30.897 42.428 30.576999999999998 42.464 30.257 42.5 C 29.726000000000003 42.56 29.195 42.62 28.685000000000002 42.661 C 26.205000000000002 42.856 23.393 43.08 20.932000000000002 42.176 C 20.776000000000003 42.119 20.622000000000003 42.058 20.469 41.996 C 20.146 41.867000000000004 19.823 41.739000000000004 19.489 41.644000000000005 C 18.905 41.477000000000004 18.310000000000002 41.415000000000006 17.728 41.355000000000004 C 16.064 41.18300000000001 13.773000000000001 40.88100000000001 11.558000000000002 40.588 C 9.508000000000003 40.317 7.393000000000002 40.039 5.7650000000000015 39.862 C 5.671000000000001 39.255 5.630000000000002 38.484 5.5870000000000015 37.676 C 5.499000000000001 36.02 5.408000000000001 34.308 4.852000000000001 33.226 C 4.557 32.655 4.331 32.3 4.16 32.032 C 3.794 31.457999999999995 3.7560000000000002 31.396999999999995 3.821 30.004999999999995 C 3.853 29.318999999999996 4.0440000000000005 28.647999999999996 4.246 27.937999999999995 C 4.3260000000000005 27.655999999999995 4.406000000000001 27.374999999999996 4.476000000000001 27.090999999999994 C 5.258000000000001 23.941999999999993 5.1930000000000005 22.225999999999992 4.9990000000000006 19.217999999999993 C 4.984000000000001 18.990999999999993 5.017 18.568999999999992 5.054 18.078999999999994 C 5.142 16.930999999999994 5.2620000000000005 15.345999999999993 4.973 14.019999999999992 C 9.151 15.748999999999992 13.527999999999999 17.214999999999993 17.975 17.993999999999993 C 20.425 18.42299999999999 22.976000000000003 19.29799999999999 25.495 18.98399999999999 C 27.836000000000002 18.69299999999999 29.969 18.132999999999992 32.313 18.060999999999993 C 32.114000000000004 18.472999999999992 31.945000000000004 18.89999999999999 31.814000000000004 19.34199999999999 C 31.668000000000003 19.83799999999999 31.568000000000005 20.342999999999993 31.472000000000005 20.82999999999999 C 31.356000000000005 21.41999999999999 31.246000000000006 21.975999999999992 31.061000000000003 22.51199999999999 C 30.897000000000002 22.98899999999999 30.676000000000002 23.44299999999999 30.442000000000004 23.92399999999999 C 30.214000000000002 24.38999999999999 30.004000000000005 25.06999999999999 29.782000000000004 25.79099999999999 C 29.580000000000002 26.44199999999999 29.372000000000003 27.11699999999999 29.179000000000002 27.51499999999999 C 28.965000000000003 27.95299999999999 28.896 28.79599999999999 28.942000000000004 29.18399999999999 C 29.194000000000003 31.27499999999999 29.687000000000005 32.48799999999999 30.164000000000005 33.65999999999999 C 30.637000000000004 34.822999999999986 31.084000000000007 35.92199999999999 31.319000000000006 37.87899999999999 C 31.478000000000005 39.19399999999999 31.658000000000005 40.68599999999999 31.281000000000006 42.00899999999999 C 31.262 42.081 31.226 42.227 31.212 42.396 z M 41.292 20.405 C 41.156 20.865000000000002 41.016 21.341 40.956 21.845000000000002 C 40.901 22.310000000000002 40.918000000000006 22.767000000000003 40.936 23.217000000000002 C 40.989 24.559 40.887 25.938000000000002 40.79 27.271 C 40.638999999999996 29.317 40.494 31.432000000000002 40.878 33.514 C 40.583 33.928000000000004 40.294 34.35 40.012 34.782000000000004 C 38.983000000000004 36.362 38.011 37.854000000000006 36.408 38.45 C 36.021 38.595000000000006 33.789 40.330000000000005 32.401 41.547000000000004 C 32.609 40.258 32.455000000000005 38.943000000000005 32.313 37.75900000000001 C 32.061 35.668000000000006 31.568 34.455000000000005 31.091 33.28300000000001 C 30.618000000000002 32.12000000000001 30.171 31.021000000000008 29.936 29.064000000000007 C 29.901 28.775000000000006 29.981 28.152000000000008 30.078 27.952000000000005 C 30.306 27.486000000000004 30.516 26.806000000000004 30.738 26.085000000000004 C 30.94 25.434000000000005 31.148 24.759000000000004 31.342 24.361000000000004 C 31.578999999999997 23.874000000000006 31.823999999999998 23.371000000000006 32.007999999999996 22.838000000000005 C 32.214999999999996 22.237000000000005 32.336999999999996 21.620000000000005 32.45399999999999 21.025000000000006 C 32.54999999999999 20.538000000000007 32.64099999999999 20.077000000000005 32.773999999999994 19.626000000000005 C 33.025999999999996 18.773000000000003 33.42399999999999 17.979000000000006 33.956999999999994 17.265000000000004 C 34.06499999999999 17.120000000000005 34.074999999999996 16.938000000000002 34.01199999999999 16.782000000000004 C 35.50099999999999 14.764000000000003 37.28699999999999 13.005000000000003 39.35499999999999 11.570000000000004 C 39.62399999999999 11.384000000000004 39.89699999999999 11.204000000000004 40.16899999999999 11.022000000000004 C 41.00599999999999 10.468000000000004 41.87199999999999 9.895000000000003 42.61499999999999 9.165000000000004 L 42.83999999999999 8.940000000000005 C 43.17099999999999 8.605000000000004 43.48899999999999 8.287000000000004 43.83299999999999 8.131000000000006 C 43.321 12.294 42.5 16.298 41.292 20.405 z"
                            stroke-linecap="round" />
                        </g>
                      </g>
                    </g>
                  </svg>

                  ${product.product_name}
                </h3>
                <span class="text-sm text-green-600 font-semibold">Completed</span>
              </div>
              <p class="text-gray-600 mt-1 text-sm">Product sold</p>
            </div>
                    `
            }
            productsContainer.insertAdjacentHTML("afterbegin", html);
            hideSkeleton();
          }
        })
        .catch(
          (error) => {
            console.error("Error fetching products:", error);
            hideSkeleton();
          }
        );
}
