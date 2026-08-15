document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("#surveyForm");
  if (!form) return;

  const slides = Array.from(document.querySelectorAll(".slide"));
  const progressBar = document.querySelector("#progressBar");
  const progressText = document.querySelector("#progressText");
  const otherCheckbox = document.querySelector("#otherActivity");
  const otherField = document.querySelector("#otherActivityField");
  let currentIndex = 0;
  let autoAdvanceTimer = null;

  function showSlide(index) {
    window.clearTimeout(autoAdvanceTimer);
    currentIndex = Math.max(0, Math.min(index, slides.length - 1));
    slides.forEach((slide, slideIndex) => {
      slide.classList.toggle("active", slideIndex === currentIndex);
    });

    const slide = slides[currentIndex];
    const questionNumber = Number(slide.dataset.question || 0);
    if (slide.dataset.step === "profile") {
      progressText.textContent = "基本信息";
      progressBar.style.width = "0%";
    } else if (slide.dataset.step === "activities") {
      progressText.textContent = "最后一题";
      progressBar.style.width = "100%";
    } else {
      progressText.textContent = `${questionNumber} / 32`;
      progressBar.style.width = `${(questionNumber / 33) * 100}%`;
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function setError(slide, message) {
    const error = slide.querySelector(".form-error");
    if (error) error.textContent = message;
  }

  function validateProfile() {
    const slide = slides[0];
    const fields = Array.from(slide.querySelectorAll("input, select"));
    const invalid = fields.find((field) => !field.checkValidity());
    if (invalid) {
      setError(slide, "请完整填写有效的个人信息后继续。");
      invalid.focus();
      return false;
    }
    setError(slide, "");
    return true;
  }

  function validateActivities() {
    const slide = slides[slides.length - 1];
    const checked = form.querySelectorAll('input[name="activities"]:checked');
    const otherText = form.elements.activity_other;
    if (!checked.length) {
      setError(slide, "请至少选择一种活动形式。");
      return false;
    }
    if (otherCheckbox.checked && !otherText.value.trim()) {
      setError(slide, "请填写你期待的其他活动形式。");
      otherText.focus();
      return false;
    }
    setError(slide, "");
    return true;
  }

  document.querySelectorAll("[data-next]").forEach((button) => {
    button.addEventListener("click", () => {
      if (currentIndex === 0 && !validateProfile()) return;
      const slide = slides[currentIndex];
      if (slide.dataset.step === "question") {
        const selected = slide.querySelector('input[type="radio"]:checked');
        if (!selected) return;
      }
      showSlide(currentIndex + 1);
    });
  });

  document.querySelectorAll("[data-back]").forEach((button) => {
    button.addEventListener("click", () => showSlide(currentIndex - 1));
  });

  document.querySelectorAll('.slide[data-step="question"]').forEach((slide) => {
    const nextButton = slide.querySelector("[data-next]");
    const radios = slide.querySelectorAll('input[type="radio"]');
    radios.forEach((radio) => {
      radio.addEventListener("change", () => {
        nextButton.disabled = false;
        const expectedIndex = slides.indexOf(slide);
        window.clearTimeout(autoAdvanceTimer);
        autoAdvanceTimer = window.setTimeout(() => {
          if (currentIndex === expectedIndex) showSlide(currentIndex + 1);
        }, 320);
      });
    });
    if (slide.querySelector('input[type="radio"]:checked')) nextButton.disabled = false;
  });

  function toggleOtherField() {
    const visible = otherCheckbox.checked;
    otherField.hidden = !visible;
    form.elements.activity_other.required = visible;
    if (!visible) form.elements.activity_other.value = "";
  }

  otherCheckbox.addEventListener("change", toggleOtherField);
  toggleOtherField();

  form.addEventListener("submit", (event) => {
    if (!validateActivities()) {
      event.preventDefault();
      return;
    }
    const submitButton = form.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.textContent = "正在生成结果…";
  });

  showSlide(0);
});
