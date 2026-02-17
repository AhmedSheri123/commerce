

function googleTranslateElementInit() {
new google.translate.TranslateElement({
    pageLanguage: 'en',
    includedLanguages: 'en,zh-CN,es,ar,fr,de,ru,pt,hi,ja',
    autoDisplay: false
}, 'google_translate_element');
}



document.addEventListener("DOMContentLoaded", function () {
  const videos = document.querySelectorAll(".lazy-video");

  const observer = new IntersectionObserver((entries, obs) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const video = entry.target;

        // ضع مصدر الفيديو من data-src
        const src = video.dataset.src;
        if (src) {
          const source = document.createElement("source");
          source.src = src;
          source.type = "video/webm"; // أو نوع الفيديو المناسب
          video.appendChild(source);

          video.load(); // يبدأ تحميل الفيديو
          video.play(); // يبدأ التشغيل
        }

        // توقف عن مراقبة هذا الفيديو بعد التحميل
        obs.unobserve(video);
      }
    });
  }, {
    threshold: 0.25 // يبدأ التحميل عندما يكون 25% من الفيديو مرئي
  });

  videos.forEach(video => observer.observe(video));
});


document.addEventListener("DOMContentLoaded", function () {
  const gifs = document.querySelectorAll(".lazy-gif");

  const observer = new IntersectionObserver((entries, obs) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const img = entry.target;
        img.src = img.dataset.src; // يبدأ تحميل GIF
        obs.unobserve(img); // توقف عن المراقبة بعد التحميل
      }
    });
  }, {
    threshold: 0.1 // يبدأ التحميل عندما يظهر جزء صغير من الصورة
  });

  gifs.forEach(gif => observer.observe(gif));
});


// tocastGen
  function tocastGen(message, type){
    const container = document.querySelector('.tocast-box');
     let
    html = `



    <div id="toast-danger" class="flex items-center w-full max-w-xs p-4 mb-4 text-gray-500 bg-white rounded-lg shadow-sm dark:text-gray-400 dark:bg-gray-800" role="alert">
        <div class="inline-flex items-center justify-center shrink-0 w-8 h-8 
        ${type === 'success' ? 'text-green-500 bg-green-100 dark:bg-green-800 dark:text-green-200' : ''}
        ${type === 'error' ? 'text-red-500 bg-red-100 dark:bg-red-800 dark:text-red-200' : ''}
        ${type === 'info' ? 'text-blue-500 bg-blue-100 dark:bg-blue-800 dark:text-blue-200' : ''}
        ${type === 'warning' ? 'text-yellow-400 bg-yellow-100 dark:bg-yellow-900 dark:text-yellow-300' : ''}
        rounded-lg">
          ${type === 'error' ? '<svg class="w-5 h-5" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" viewBox="0 0 24 24"><path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18 17.94 6M18 18 6.06 6"/></svg>' : ''}
          ${type === 'success' ? '<svg class="w-5 h-5" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" viewBox="0 0 24 24"><path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 11.917 9.724 16.5 19 7.5"/></svg>' : ''}
          ${type === 'info' ? '<svg class="w-5 h-5" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" viewBox="0 0 24 24"><path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 2v2m0 4h.01M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"/></svg>' : ''}
          ${type === 'warning' ? '<svg class="w-5 h-5" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" viewBox="0 0 24 24"><path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.29 3.86 1.82 18a2.25 2.25 0 0 0 1.97 3.34h16.42a2.25 2.25 0 0 0 1.97-3.34L13.71 3.86a2.25 2.25 0 0 0-3.42 0Z"/></svg>' : ''}

            <span class="sr-only">icon</span>
        </div>
        <div class="ms-3 text-sm font-normal">${message}</div>
    <button type="button"
      class="ms-auto flex items-center justify-center h-8 w-8 rounded hover:bg-gray-200"
      onclick="this.parentElement.remove()">
      <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2"
           viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round"
              d="M6 18 18 6M6 6l12 12"/>
      </svg>
    </button>
    </div>
    `
    container.insertAdjacentHTML('afterbegin', html);
  }






// active-users
    (function () {
      var countFabEl = document.getElementById("active-users-count-fab");
      var countModalEl = document.getElementById("active-users-count-modal");
      var fabBtn = document.getElementById("active-users-fab");
      var modalEl = document.getElementById("active-users-modal");
      var closeBtn = document.getElementById("close-active-users-modal");
      var countUrl = "{% url 'accounts:active_users_count_api' %}";

      if (!fabBtn || !modalEl || !closeBtn || !countFabEl || !countModalEl) {
        return;
      }

      function refreshActiveUsersCount() {
        fetch(countUrl, {
          method: "GET",
          headers: { "X-Requested-With": "XMLHttpRequest" },
          credentials: "same-origin"
        })
          .then(function (response) {
            if (!response.ok) {
              throw new Error("Failed to fetch active users count");
            }
            return response.json();
          })
          .then(function (data) {
            if (typeof data.count === "number") {
              countFabEl.textContent = data.count;
              countModalEl.textContent = data.count;
            }
          })
          .catch(function () {
            // Keep current value if request fails.
          });
      }

      fabBtn.addEventListener("click", function () {
        modalEl.classList.remove("hidden");
        modalEl.classList.add("flex");
        modalEl.setAttribute("aria-hidden", "false");
      });

      closeBtn.addEventListener("click", function () {
        modalEl.classList.add("hidden");
        modalEl.classList.remove("flex");
        modalEl.setAttribute("aria-hidden", "true");
      });

      modalEl.addEventListener("click", function (event) {
        if (event.target === modalEl) {
          modalEl.classList.add("hidden");
          modalEl.classList.remove("flex");
          modalEl.setAttribute("aria-hidden", "true");
        }
      });

      setInterval(refreshActiveUsersCount, 5000);
    })();


// دالة لتطبيق الإخفاء على توست معين
function autoHideToast(el, delay = 6000) {
  setTimeout(() => {
    el.classList.add('toast-hide'); // أضف class الانيميشن
    setTimeout(() => el.remove(), 500); // إزالة العنصر بعد الانيميشن
  }, delay);
}

// تطبيق على كل العناصر الموجودة عند التحميل
document.querySelectorAll('.tocast-box > div').forEach(el => autoHideToast(el));

// مراقبة أي عناصر جديدة داخل tocast-box
const container = document.querySelector('.tocast-box');
const observer = new MutationObserver(mutations => {
  mutations.forEach(mutation => {
    mutation.addedNodes.forEach(node => {
      if (node.nodeType === 1 && node.matches('div')) {
        autoHideToast(node);
      }
    });
  });
});

// بدء المراقبة
observer.observe(container, { childList: true });



//showToast
function showToast(message, duration = 4000) {

    const container = document.querySelector(".tocast-box");

    const toast = document.createElement("div");

    toast.className = `
        flex items-center w-full max-w-xs p-4 rounded shadow border
        bg-gray-100 text-gray-800 border-gray-300
        opacity-0 translate-y-2 transition-all duration-300
    `;

    toast.innerHTML = `
        <!-- Avatar -->
        <div class="flex items-center justify-center w-8 h-8 rounded-full bg-gray-300 font-bold">
            SY
        </div>

        <!-- Message -->
        <div class="ms-3 text-sm flex-1">
            <div class="font-semibold">System</div>
            <div>${message}</div>
        </div>

        <!-- Close -->
        <button class="ms-2 h-7 w-7 rounded hover:bg-black/10 flex items-center justify-center">
            ✕
        </button>
    `;

    // زر الإغلاق
    toast.querySelector("button").onclick = () => removeToast(toast);

    container.appendChild(toast);

    // animation دخول
    setTimeout(() => {
        toast.classList.remove("opacity-0", "translate-y-2");
    }, 50);

    // حذف تلقائي
    setTimeout(() => removeToast(toast), duration);
}

function removeToast(toast) {
    toast.classList.add("opacity-0", "-translate-y-2");
    setTimeout(() => toast.remove(), 300);
}




function generateMaskedNumber(length = 11) {

    // توليد رقم عشوائي
    let number = "";
    for (let i = 0; i < length; i++) {
        number += Math.floor(Math.random() * 10);
    }

    // إخفاء كل شيء ما عدا آخر 4
    const last4 = number.slice(-4);
    const stars = "*".repeat(length - 4);

    const masked = stars + last4;

    return {
        full: number,
        masked: masked
    };
}


function generateNumber(min = 50, max = 5000) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

function gen_winner(){
  const money = generateNumber()
  const number = generateMaskedNumber().masked
  const msg = `Today, the owner of number "${number}" won the sum of <strong>${money}$</strong>`
  showToast(msg, duration = 4000)

}

setInterval(() => {
    gen_winner()
}, 15000); // 10000 ملي ثانية = 10 ثواني