var timeout = 10 * 1000;
var post_url = '{{ request.path }}';
$(function() {
submitForm();
});
function submitForm() {
tinyMCE.triggerSave();
var formData = $('form').serialize() + "&ajax=1";
if (typeof eid !== 'undefined' && eid > 0) {
formData += "&eid=" + eid + "&type=" + type;
}
$.ajax({
type: "POST",
url: post_url,
data: formData,
success: function(msg) {
setTimeout(confirmSubmit, 100);
if (msg.warn) alert(msg.warn);
}
});
setTimeout(submitForm, timeout);
}
function confirmSubmit() {
$('#confirm').css('color', 'green');
setTimeout(endConfirmSubmit, 1000);
}
function endConfirmSubmit() {
$('#confirm').css('color', '');
}
