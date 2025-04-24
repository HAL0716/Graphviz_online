$(function () {
  // 初期化処理
  initializeSelect2();
  initializeDefaultValues();

  // グラフ生成
  function generateGraph() {
    const data = gatherFormData();
    $.post({
      url: '/generate',
      contentType: 'application/json',
      dataType: 'json',
      data: JSON.stringify(data),
      success: handleGraphSuccess,
      error: handleGraphError
    });
  }

  // 画像の読み込み完了後にサイズ調整を行う
  function resizeGraphImage() {
    const wrapper = document.querySelector('.image-wrapper');
    const img = document.getElementById('graph-image');

    img.onload = function() {
      adjustImageSize(wrapper, img);
    };

    if (img.complete) img.onload();
  }

  // 画像のサイズ調整
  function adjustImageSize(wrapper, img) {
    const wrapperWidth = wrapper.clientWidth;
    const wrapperHeight = wrapper.clientHeight;
    const imgNaturalWidth = img.naturalWidth;
    const imgNaturalHeight = img.naturalHeight;

    if (imgNaturalWidth && imgNaturalHeight) {
      const ratio = Math.min(wrapperWidth / imgNaturalWidth, wrapperHeight / imgNaturalHeight);
      img.style.width = `${imgNaturalWidth * ratio}px`;
      img.style.height = `${imgNaturalHeight * ratio}px`;
    }
  }

  // フォームデータをまとめる
  function gatherFormData() {
    return {
      symbols: $('#symbols').val(),
      period: $('#period').val(),
      forbiddenLength: $('#forbidden-length').val(),
      forbiddenWords: $('#forbidden-words').val(),
      essentialize: $('#essentialize').is(':checked'),
      minimize: $('#minimize').is(':checked'),
      nodeHeight: $('#node-h').val(),
      nodeWidth: $('#node-w').val(),
      spacingY: $('#space-y').val(),
      spacingX: $('#space-x').val()
    };
  }

  // グラフ生成後の成功時処理
  function handleGraphSuccess(res) {
    if (res.image_url) {
      $('#graph-image').attr('src', res.image_url);
      resizeGraphImage();
    } else {
      console.error('画像生成エラー:', res.error);
    }

    const value = res.eigen_value ? parseFloat(res.eigen_value).toFixed(6) : '-';
    updateEigenvalueLabel(value);
  }

  // グラフ生成エラー時処理
  function handleGraphError() {
    alert('グラフ生成中にエラーが発生しました');
  }

  // 固有値ラベルの更新
  function updateEigenvalueLabel(value) {
    const labelBase = $('#eigenvalue').text().split(':')[0];
    $('#eigenvalue').text(`${labelBase} : ${value}`).attr('data-value', value);
  }

  // カウントの更新
  function updateCounts() {
    $('#symbol-count-label').text(`シンボル数 : ${$('#symbols').val().length}`);
    $('#forbidden-count-label').text(`禁止語数 : ${$('#forbidden-words').val().length}`);
    generateGraph();
  }

  // 禁止語の更新
  function updateForbiddenWords() {
    const data = {
      symbols: $('#symbols').val(),
      length: $('#forbidden-length').val()
    };
    $.post({
      url: '/get_forbidden_words',
      contentType: 'application/json',
      dataType: 'json',
      data: JSON.stringify(data),
      success: populateForbiddenWords,
      error: handleForbiddenWordsError
    });
  }

  // 禁止語リストの更新
  function populateForbiddenWords(data) {
    const $fw = $('#forbidden-words').empty();
    data.forEach(w => $fw.append(new Option(w, w)));
    $fw.val([data[0]]).trigger('change');
  }

  // 禁止語取得エラー時の処理
  function handleForbiddenWordsError() {
    alert('禁止語の取得に失敗しました');
  }

  // スライダーのイベントを設定
  function bindSlider(id, labelId, decimalPlaces = 1) {
    $(`#${id}`).on('input', function () {
      const value = parseFloat(this.value).toFixed(decimalPlaces);
      updateLabelValue(labelId, value);
      generateGraph();
    });
  }

  // ラベルの更新
  function updateLabelValue(labelId, value) {
    const labelBase = $(`#${labelId}`).text().split(':')[0];
    $(`#${labelId}`).text(`${labelBase} : ${value}`).attr('data-value', value);
  }

  // 初期化設定
  function initializeSelect2() {
    $('#symbols, #forbidden-words').select2({ placeholder: '選択してください', width: '100%' });
  }

  function initializeDefaultValues() {
    $('#symbols').val(['0', '1']).trigger('change');
    $('#period, #forbidden-length').val(2);
  }

  // 高さ調整
  function adjustMainHeight() {
    const side = document.querySelector('.side');
    const main = document.querySelector('.main');
    if (side && main) main.style.height = `${side.getBoundingClientRect().height}px`;
  }

  // イベントバインド
  [
    { id: 'period', decimals: 0 },
    { id: 'forbidden-length', decimals: 0 },
    { id: 'node-h', decimals: 1 },
    { id: 'node-w', decimals: 1 },
    { id: 'space-y', decimals: 1 },
    { id: 'space-x', decimals: 1 }
  ].forEach(({ id, decimals }) => {
    bindSlider(id, `${id}-label`, decimals);
  });

  $('#symbols').on('change', updateForbiddenWords);
  $('#forbidden-length').on('change', updateForbiddenWords);
  $('#forbidden-words').on('change', updateCounts);

  $('#essentialize').on('change', function () {
    const on = $(this).is(':checked');
    $('#minimize').prop('disabled', !on);
    if (!on) $('#minimize').prop('checked', false);
    generateGraph();
  });

  $('#minimize').on('change', function () {
    if (!$('#essentialize').is(':checked')) {
      $(this).prop('checked', false);
      return;
    }
    generateGraph();
  });

  $('#save-btn').on('click', function () {
    const formats = $('input[type="checkbox"]:checked').map((_, el) => el.id).get();
    if (!formats.length) return alert('少なくとも1つの形式を選択してください。');
    location.href = `/download?${formats.map(f => `ext=${encodeURIComponent(f)}`).join('&')}`;
  });

  updateForbiddenWords();

  // ウィンドウの読み込みおよびリサイズ時に高さ調整
  window.addEventListener('load', adjustMainHeight);
  window.addEventListener('resize', adjustMainHeight);
});