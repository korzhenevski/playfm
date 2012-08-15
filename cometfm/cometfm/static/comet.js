// Constructor.
// Based on Dklab_Realplexor
// Create new Comet object.
function Comet(fullUrl)
{
	// Current JS library version.
	var VERSION = "1.32";

	// Detect current page hostname.
	var host = document.location.host;
	
	// Assign initial properties.
	if (!this.constructor._registry) this.constructor._registry = {}; // all objects registry
	this.version = VERSION;
	this.callback = {};
	this._realplexor = null;
	this._iframeId = "mpl" + (new Date().getTime());
	this._iframeTag = 
		'<iframe'
		+ ' id="' + this._iframeId + '"'
		+ ' onload="' + 'Comet' + '._iframeLoaded(&quot;' + this._iframeId + '&quot;)"'
		+ ' src="' + fullUrl + '?HOST=' + host + '&amp;version=' + this.version + '"'
		+ ' style="position:absolute; visibility:hidden; width:200px; height:200px; left:-1000px; top:-1000px"' +
		'></iframe>';
	this._iframeCreated = false;
	this._needExecute = false;
	this._executeTimer = null;
	
	// Register this object in the registry (for IFRAME onload callback).
	this.constructor._registry[this._iframeId] = this;

	// Allow realplexor's IFRAME to access outer window.
	document.domain = host;	
}

// Static function. 
// Called when a realplexor iframe is loaded.
Comet._iframeLoaded = function(id)
{
	var th = this._registry[id];
	// use setTimeout to let IFRAME JavaScript code some time to execute.
	setTimeout(function() {
		var iframe = document.getElementById(id);
		th._realplexor = iframe.contentWindow.Comet_Loader;
		if (th.needExecute) {
			th.execute();
		}
	}, 50);
}

// Subscribe a new callback to specified ID.
// To apply changes and reconnect to the server, call execute()
// after a sequence of subscribe() calls.
Comet.prototype.subscribe = function(id, params, callback) {
    this.callback = {id: id, params: $.param(params), callback: callback};
    this.execute();
}

// Reconnect to the server and listen for all specified IDs.
// You should call this method after a number of calls to subscribe().
Comet.prototype.execute = function() {
	// Control IFRAME creation.
	if (!this._iframeCreated) {
		var div = document.createElement('DIV');
		div.innerHTML = this._iframeTag;
		document.body.appendChild(div);
		this._iframeCreated = true;
	}
	
	// Check if the realplexor is ready (if not, schedule later execution).
	if (this._executeTimer) {
		clearTimeout(this._executeTimer);
		this._executeTimer = null;
	}
	var th = this;
	if (!this._realplexor) {
		this._executeTimer = setTimeout(function() { th.execute() }, 30);
		return;
	}
	
	// Realplexor loader is ready, run it.
	this._realplexor.execute(
		this.callback,
		this.constructor._callAndReturnException
	);
}

// This is a work-around for stupid IE. Unfortunately IE cannot
// catch exceptions which are thrown from the different frame
// (in most cases). Please see
// http://blogs.msdn.com/jaiprakash/archive/2007/01/22/jscript-exceptions-not-handled-thrown-across-frames-if-thrown-from-a-expando-method.aspx
Comet._callAndReturnException = function(func, args) {
	try {
		func.apply(null, args);
		return null;
	} catch (e) {
		return "" + e;
	}
}
