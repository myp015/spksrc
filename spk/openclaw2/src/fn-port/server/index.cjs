"use strict";
var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __commonJS = (cb, mod) => function __require() {
  return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));

// ../../node_modules/.pnpm/ws@8.19.0/node_modules/ws/lib/constants.js
var require_constants = __commonJS({
  "../../node_modules/.pnpm/ws@8.19.0/node_modules/ws/lib/constants.js"(exports2, module2) {
    "use strict";
    var BINARY_TYPES = ["nodebuffer", "arraybuffer", "fragments"];
    var hasBlob = typeof Blob !== "undefined";
    if (hasBlob) BINARY_TYPES.push("blob");
    module2.exports = {
      BINARY_TYPES,
      CLOSE_TIMEOUT: 3e4,
      EMPTY_BUFFER: Buffer.alloc(0),
      GUID: "258EAFA5-E914-47DA-95CA-C5AB0DC85B11",
      hasBlob,
      kForOnEventAttribute: Symbol("kIsForOnEventAttribute"),
      kListener: Symbol("kListener"),
      kStatusCode: Symbol("status-code"),
      kWebSocket: Symbol("websocket"),
      NOOP: () => {
      }
    };
  }
});

// ../../node_modules/.pnpm/ws@8.19.0/node_modules/ws/lib/buffer-util.js
var require_buffer_util = __commonJS({
  "../../node_modules/.pnpm/ws@8.19.0/node_modules/ws/lib/buffer-util.js"(exports2, module2) {
    "use strict";
    var { EMPTY_BUFFER } = require_constants();
    var FastBuffer = Buffer[Symbol.species];
    function concat(list, totalLength) {
      if (list.length === 0) return EMPTY_BUFFER;
      if (list.length === 1) return list[0];
      const target = Buffer.allocUnsafe(totalLength);
      let offset = 0;
      for (let i = 0; i < list.length; i++) {
        const buf = list[i];
        target.set(buf, offset);
        offset += buf.length;
      }
      if (offset < totalLength) {
        return new FastBuffer(target.buffer, target.byteOffset, offset);
      }
      return target;
    }
    function _mask(source, mask, output, offset, length) {
      for (let i = 0; i < length; i++) {
        output[offset + i] = source[i] ^ mask[i & 3];
      }
    }
    function _unmask(buffer, mask) {
      for (let i = 0; i < buffer.length; i++) {
        buffer[i] ^= mask[i & 3];
      }
    }
    function toArrayBuffer(buf) {
      if (buf.length === buf.buffer.byteLength) {
        return buf.buffer;
      }
      return buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.length);
    }
    function toBuffer(data) {
      toBuffer.readOnly = true;
      if (Buffer.isBuffer(data)) return data;
      let buf;
      if (data instanceof ArrayBuffer) {
        buf = new FastBuffer(data);
      } else if (ArrayBuffer.isView(data)) {
        buf = new FastBuffer(data.buffer, data.byteOffset, data.byteLength);
      } else {
        buf = Buffer.from(data);
        toBuffer.readOnly = false;
      }
      return buf;
    }
    module2.exports = {
      concat,
      mask: _mask,
      toArrayBuffer,
      toBuffer,
      unmask: _unmask
    };
    if (!process.env.WS_NO_BUFFER_UTIL) {
      try {
        const bufferUtil = require("bufferutil");
        module2.exports.mask = function(source, mask, output, offset, length) {
          if (length < 48) _mask(source, mask, output, offset, length);
          else bufferUtil.mask(source, mask, output, offset, length);
        };
        module2.exports.unmask = function(buffer, mask) {
          if (buffer.length < 32) _unmask(buffer, mask);
          else bufferUtil.unmask(buffer, mask);
        };
      } catch (e) {
      }
    }
  }
});

// ../../node_modules/.pnpm/ws@8.19.0/node_modules/ws/lib/limiter.js
var require_limiter = __commonJS({
  "../../node_modules/.pnpm/ws@8.19.0/node_modules/ws/lib/limiter.js"(exports2, module2) {
    "use strict";
    var kDone = Symbol("kDone");
    var kRun = Symbol("kRun");
    var Limiter = class {
      /**
       * Creates a new `Limiter`.
       *
       * @param {Number} [concurrency=Infinity] The maximum number of jobs allowed
       *     to run concurrently
       */
      constructor(concurrency) {
        this[kDone] = () => {
          this.pending--;
          this[kRun]();
        };
        this.concurrency = concurrency || Infinity;
        this.jobs = [];
        this.pending = 0;
      }
      /**
       * Adds a job to the queue.
       *
       * @param {Function} job The job to run
       * @public
       */
      add(job) {
        this.jobs.push(job);
        this[kRun]();
      }
      /**
       * Removes a job from the queue and runs it if possible.
       *
       * @private
       */
      [kRun]() {
        if (this.pending === this.concurrency) return;
        if (this.jobs.length) {
          const job = this.jobs.shift();
          this.pending++;
          job(this[kDone]);
        }
      }
    };
    module2.exports = Limiter;
  }
});

// ../../node_modules/.pnpm/ws@8.19.0/node_modules/ws/lib/permessage-deflate.js
var require_permessage_deflate = __commonJS({
  "../../node_modules/.pnpm/ws@8.19.0/node_modules/ws/lib/permessage-deflate.js"(exports2, module2) {
    "use strict";
    var zlib = require("zlib");
    var bufferUtil = require_buffer_util();
    var Limiter = require_limiter();
    var { kStatusCode } = require_constants();
    var FastBuffer = Buffer[Symbol.species];
    var TRAILER = Buffer.from([0, 0, 255, 255]);
    var kPerMessageDeflate = Symbol("permessage-deflate");
    var kTotalLength = Symbol("total-length");
    var kCallback = Symbol("callback");
    var kBuffers = Symbol("buffers");
    var kError = Symbol("error");
    var zlibLimiter;
    var PerMessageDeflate = class {
      /**
       * Creates a PerMessageDeflate instance.
       *
       * @param {Object} [options] Configuration options
       * @param {(Boolean|Number)} [options.clientMaxWindowBits] Advertise support
       *     for, or request, a custom client window size
       * @param {Boolean} [options.clientNoContextTakeover=false] Advertise/
       *     acknowledge disabling of client context takeover
       * @param {Number} [options.concurrencyLimit=10] The number of concurrent
       *     calls to zlib
       * @param {(Boolean|Number)} [options.serverMaxWindowBits] Request/confirm the
       *     use of a custom server window size
       * @param {Boolean} [options.serverNoContextTakeover=false] Request/accept
       *     disabling of server context takeover
       * @param {Number} [options.threshold=1024] Size (in bytes) below which
       *     messages should not be compressed if context takeover is disabled
       * @param {Object} [options.zlibDeflateOptions] Options to pass to zlib on
       *     deflate
       * @param {Object} [options.zlibInflateOptions] Options to pass to zlib on
       *     inflate
       * @param {Boolean} [isServer=false] Create the instance in either server or
       *     client mode
       * @param {Number} [maxPayload=0] The maximum allowed message length
       */
      constructor(options, isServer, maxPayload) {
        this._maxPayload = maxPayload | 0;
        this._options = options || {};
        this._threshold = this._options.threshold !== void 0 ? this._options.threshold : 1024;
        this._isServer = !!isServer;
        this._deflate = null;
        this._inflate = null;
        this.params = null;
        if (!zlibLimiter) {
          const concurrency = this._options.concurrencyLimit !== void 0 ? this._options.concurrencyLimit : 10;
          zlibLimiter = new Limiter(concurrency);
        }
      }
      /**
       * @type {String}
       */
      static get extensionName() {
        return "permessage-deflate";
      }
      /**
       * Create an extension negotiation offer.
       *
       * @return {Object} Extension parameters
       * @public
       */
      offer() {
        const params = {};
        if (this._options.serverNoContextTakeover) {
          params.server_no_context_takeover = true;
        }
        if (this._options.clientNoContextTakeover) {
          params.client_no_context_takeover = true;
        }
        if (this._options.serverMaxWindowBits) {
          params.server_max_window_bits = this._options.serverMaxWindowBits;
        }
        if (this._options.clientMaxWindowBits) {
          params.client_max_window_bits = this._options.clientMaxWindowBits;
        } else if (this._options.clientMaxWindowBits == null) {
          params.client_max_window_bits = true;
        }
        return params;
      }
      /**
       * Accept an extension negotiation offer/response.
       *
       * @param {Array} configurations The extension negotiation offers/reponse
       * @return {Object} Accepted configuration
       * @public
       */
      accept(configurations) {
        configurations = this.normalizeParams(configurations);
        this.params = this._isServer ? this.acceptAsServer(configurations) : this.acceptAsClient(configurations);
        return this.params;
      }
      /**
       * Releases all resources used by the extension.
       *
       * @public
       */
      cleanup() {
        if (this._inflate) {
          this._inflate.close();
          this._inflate = null;
        }
        if (this._deflate) {
          const callback = this._deflate[kCallback];
          this._deflate.close();
          this._deflate = null;
          if (callback) {
            callback(
              new Error(
                "The deflate stream was closed while data was being processed"
              )
            );
          }
        }
      }
      /**
       *  Accept an extension negotiation offer.
       *
       * @param {Array} offers The extension negotiation offers
       * @return {Object} Accepted configuration
       * @private
       */
      acceptAsServer(offers) {
        const opts = this._options;
        const accepted = offers.find((params) => {
          if (opts.serverNoContextTakeover === false && params.server_no_context_takeover || params.server_max_window_bits && (opts.serverMaxWindowBits === false || typeof opts.serverMaxWindowBits === "number" && opts.serverMaxWindowBits > params.server_max_window_bits) || typeof opts.clientMaxWindowBits === "number" && !params.client_max_window_bits) {
            return false;
          }
          return true;
        });
        if (!accepted) {
          throw new Error("None of the extension offers can be accepted");
        }
        if (opts.serverNoContextTakeover) {
          accepted.server_no_context_takeover = true;
        }
        if (opts.clientNoContextTakeover) {
          accepted.client_no_context_takeover = true;
        }
        if (typeof opts.serverMaxWindowBits === "number") {
          accepted.server_max_window_bits = opts.serverMaxWindowBits;
        }
        if (typeof opts.clientMaxWindowBits === "number") {
          accepted.client_max_window_bits = opts.clientMaxWindowBits;
        } else if (accepted.client_max_window_bits === true || opts.clientMaxWindowBits === false) {
          delete accepted.client_max_window_bits;
        }
        return accepted;
      }
      /**
       * Accept the extension negotiation response.
       *
       * @param {Array} response The extension negotiation response
       * @return {Object} Accepted configuration
       * @private
       */
      acceptAsClient(response) {
        const params = response[0];
        if (this._options.clientNoContextTakeover === false && params.client_no_context_takeover) {
          throw new Error('Unexpected parameter "client_no_context_takeover"');
        }
        if (!params.client_max_window_bits) {
          if (typeof this._options.clientMaxWindowBits === "number") {
            params.client_max_window_bits = this._options.clientMaxWindowBits;
          }
        } else if (this._options.clientMaxWindowBits === false || typeof this._options.clientMaxWindowBits === "number" && params.client_max_window_bits > this._options.clientMaxWindowBits) {
          throw new Error(
            'Unexpected or invalid parameter "client_max_window_bits"'
          );
        }
        return params;
      }
      /**
       * Normalize parameters.
       *
       * @param {Array} configurations The extension negotiation offers/reponse
       * @return {Array} The offers/response with normalized parameters
       * @private
       */
      normalizeParams(configurations) {
        configurations.forEach((params) => {
          Object.keys(params).forEach((key) => {
            let value = params[key];
            if (value.length > 1) {
              throw new Error(`Parameter "${key}" must have only a single value`);
            }
            value = value[0];
            if (key === "client_max_window_bits") {
              if (value !== true) {
                const num = +value;
                if (!Number.isInteger(num) || num < 8 || num > 15) {
                  throw new TypeError(
                    `Invalid value for parameter "${key}": ${value}`
                  );
                }
                value = num;
              } else if (!this._isServer) {
                throw new TypeError(
                  `Invalid value for parameter "${key}": ${value}`
                );
              }
            } else if (key === "server_max_window_bits") {
              const num = +value;
              if (!Number.isInteger(num) || num < 8 || num > 15) {
                throw new TypeError(
                  `Invalid value for parameter "${key}": ${value}`
                );
              }
              value = num;
            } else if (key === "client_no_context_takeover" || key === "server_no_context_takeover") {
              if (value !== true) {
                throw new TypeError(
                  `Invalid value for parameter "${key}": ${value}`
                );
              }
            } else {
              throw new Error(`Unknown parameter "${key}"`);
            }
            params[key] = value;
          });
        });
        return configurations;
      }
      /**
       * Decompress data. Concurrency limited.
       *
       * @param {Buffer} data Compressed data
       * @param {Boolean} fin Specifies whether or not this is the last fragment
       * @param {Function} callback Callback
       * @public
       */
      decompress(data, fin, callback) {
        zlibLimiter.add((done) => {
          this._decompress(data, fin, (err, result) => {
            done();
            callback(err, result);
          });
        });
      }
      /**
       * Compress data. Concurrency limited.
       *
       * @param {(Buffer|String)} data Data to compress
       * @param {Boolean} fin Specifies whether or not this is the last fragment
       * @param {Function} callback Callback
       * @public
       */
      compress(data, fin, callback) {
        zlibLimiter.add((done) => {
          this._compress(data, fin, (err, result) => {
            done();
            callback(err, result);
          });
        });
      }
      /**
       * Decompress data.
       *
       * @param {Buffer} data Compressed data
       * @param {Boolean} fin Specifies whether or not this is the last fragment
       * @param {Function} callback Callback
       * @private
       */
      _decompress(data, fin, callback) {
        const endpoint = this._isServer ? "client" : "server";
        if (!this._inflate) {
          const key = `${endpoint}_max_window_bits`;
          const windowBits = typeof this.params[key] !== "number" ? zlib.Z_DEFAULT_WINDOWBITS : this.params[key];
          this._inflate = zlib.createInflateRaw({
            ...this._options.zlibInflateOptions,
            windowBits
          });
          this._inflate[kPerMessageDeflate] = this;
          this._inflate[kTotalLength] = 0;
          this._inflate[kBuffers] = [];
          this._inflate.on("error", inflateOnError);
          this._inflate.on("data", inflateOnData);
        }
        this._inflate[kCallback] = callback;
        this._inflate.write(data);
        if (fin) this._inflate.write(TRAILER);
        this._inflate.flush(() => {
          const err = this._inflate[kError];
          if (err) {
            this._inflate.close();
            this._inflate = null;
            callback(err);
            return;
          }
          const data2 = bufferUtil.concat(
            this._inflate[kBuffers],
            this._inflate[kTotalLength]
          );
          if (this._inflate._readableState.endEmitted) {
            this._inflate.close();
            this._inflate = null;
          } else {
            this._inflate[kTotalLength] = 0;
            this._inflate[kBuffers] = [];
            if (fin && this.params[`${endpoint}_no_context_takeover`]) {
              this._inflate.reset();
            }
          }
          callback(null, data2);
        });
      }
      /**
       * Compress data.
       *
       * @param {(Buffer|String)} data Data to compress
       * @param {Boolean} fin Specifies whether or not this is the last fragment
       * @param {Function} callback Callback
       * @private
       */
      _compress(data, fin, callback) {
        const endpoint = this._isServer ? "server" : "client";
        if (!this._deflate) {
          const key = `${endpoint}_max_window_bits`;
          const windowBits = typeof this.params[key] !== "number" ? zlib.Z_DEFAULT_WINDOWBITS : this.params[key];
          this._deflate = zlib.createDeflateRaw({
            ...this._options.zlibDeflateOptions,
            windowBits
          });
          this._deflate[kTotalLength] = 0;
          this._deflate[kBuffers] = [];
          this._deflate.on("data", deflateOnData);
        }
        this._deflate[kCallback] = callback;
        this._deflate.write(data);
        this._deflate.flush(zlib.Z_SYNC_FLUSH, () => {
          if (!this._deflate) {
            return;
          }
          let data2 = bufferUtil.concat(
            this._deflate[kBuffers],
            this._deflate[kTotalLength]
          );
          if (fin) {
            data2 = new FastBuffer(data2.buffer, data2.byteOffset, data2.length - 4);
          }
          this._deflate[kCallback] = null;
          this._deflate[kTotalLength] = 0;
          this._deflate[kBuffers] = [];
          if (fin && this.params[`${endpoint}_no_context_takeover`]) {
            this._deflate.reset();
          }
          callback(null, data2);
        });
      }
    };
    module2.exports = PerMessageDeflate;
    function deflateOnData(chunk) {
      this[kBuffers].push(chunk);
      this[kTotalLength] += chunk.length;
    }
    function inflateOnData(chunk) {
      this[kTotalLength] += chunk.length;
      if (this[kPerMessageDeflate]._maxPayload < 1 || this[kTotalLength] <= this[kPerMessageDeflate]._maxPayload) {
        this[kBuffers].push(chunk);
        return;
      }
      this[kError] = new RangeError("Max payload size exceeded");
      this[kError].code = "WS_ERR_UNSUPPORTED_MESSAGE_LENGTH";
      this[kError][kStatusCode] = 1009;
      this.removeListener("data", inflateOnData);
      this.reset();
    }
    function inflateOnError(err) {
      this[kPerMessageDeflate]._inflate = null;
      if (this[kError]) {
        this[kCallback](this[kError]);
        return;
      }
      err[kStatusCode] = 1007;
      this[kCallback](err);
    }
  }
});

// ../../node_modules/.pnpm/ws@8.19.0/node_modules/ws/lib/validation.js
var require_validation = __commonJS({
  "../../node_modules/.pnpm/ws@8.19.0/node_modules/ws/lib/validation.js"(exports2, module2) {
    "use strict";
    var { isUtf8 } = require("buffer");
    var { hasBlob } = require_constants();
    var tokenChars = [
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      // 0 - 15
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      // 16 - 31
      0,
      1,
      0,
      1,
      1,
      1,
      1,
      1,
      0,
      0,
      1,
      1,
      0,
      1,
      1,
      0,
      // 32 - 47
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      0,
      0,
      0,
      0,
      0,
      0,
      // 48 - 63
      0,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      // 64 - 79
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      0,
      0,
      0,
      1,
      1,
      // 80 - 95
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      // 96 - 111
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      1,
      0,
      1,
      0,
      1,
      0
      // 112 - 127
    ];
    function isValidStatusCode(code) {
      return code >= 1e3 && code <= 1014 && code !== 1004 && code !== 1005 && code !== 1006 || code >= 3e3 && code <= 4999;
    }
    function _isValidUTF8(buf) {
      const len = buf.length;
      let i = 0;
      while (i < len) {
        if ((buf[i] & 128) === 0) {
          i++;
        } else if ((buf[i] & 224) === 192) {
          if (i + 1 === len || (buf[i + 1] & 192) !== 128 || (buf[i] & 254) === 192) {
            return false;
          }
          i += 2;
        } else if ((buf[i] & 240) === 224) {
          if (i + 2 >= len || (buf[i + 1] & 192) !== 128 || (buf[i + 2] & 192) !== 128 || buf[i] === 224 && (buf[i + 1] & 224) === 128 || // Overlong
          buf[i] === 237 && (buf[i + 1] & 224) === 160) {
            return false;
          }
          i += 3;
        } else if ((buf[i] & 248) === 240) {
          if (i + 3 >= len || (buf[i + 1] & 192) !== 128 || (buf[i + 2] & 192) !== 128 || (buf[i + 3] & 192) !== 128 || buf[i] === 240 && (buf[i + 1] & 240) === 128 || // Overlong
          buf[i] === 244 && buf[i + 1] > 143 || buf[i] > 244) {
            return false;
          }
          i += 4;
        } else {
          return false;
        }
      }
      return true;
    }
    function isBlob(value) {
      return hasBlob && typeof value === "object" && typeof value.arrayBuffer === "function" && typeof value.type === "string" && typeof value.stream === "function" && (value[Symbol.toStringTag] === "Blob" || value[Symbol.toStringTag] === "File");
    }
    module2.exports = {
      isBlob,
      isValidStatusCode,
      isValidUTF8: _isValidUTF8,
      tokenChars
    };
    if (isUtf8) {
      module2.exports.isValidUTF8 = function(buf) {
        return buf.length < 24 ? _isValidUTF8(buf) : isUtf8(buf);
      };
    } else if (!process.env.WS_NO_UTF_8_VALIDATE) {
      try {
        const isValidUTF8 = require("utf-8-validate");
        module2.exports.isValidUTF8 = function(buf) {
          return buf.length < 32 ? _isValidUTF8(buf) : isValidUTF8(buf);
        };
      } catch (e) {
      }
    }
  }
});

// ../../node_modules/.pnpm/ws@8.19.0/node_modules/ws/lib/receiver.js
var require_receiver = __commonJS({
  "../../node_modules/.pnpm/ws@8.19.0/node_modules/ws/lib/receiver.js"(exports2, module2) {
    "use strict";
    var { Writable } = require("stream");
    var PerMessageDeflate = require_permessage_deflate();
    var {
      BINARY_TYPES,
      EMPTY_BUFFER,
      kStatusCode,
      kWebSocket
    } = require_constants();
    var { concat, toArrayBuffer, unmask } = require_buffer_util();
    var { isValidStatusCode, isValidUTF8 } = require_validation();
    var FastBuffer = Buffer[Symbol.species];
    var GET_INFO = 0;
    var GET_PAYLOAD_LENGTH_16 = 1;
    var GET_PAYLOAD_LENGTH_64 = 2;
    var GET_MASK = 3;
    var GET_DATA = 4;
    var INFLATING = 5;
    var DEFER_EVENT = 6;
    var Receiver2 = class extends Writable {
      /**
       * Creates a Receiver instance.
       *
       * @param {Object} [options] Options object
       * @param {Boolean} [options.allowSynchronousEvents=true] Specifies whether
       *     any of the `'message'`, `'ping'`, and `'pong'` events can be emitted
       *     multiple times in the same tick
       * @param {String} [options.binaryType=nodebuffer] The type for binary data
       * @param {Object} [options.extensions] An object containing the negotiated
       *     extensions
       * @param {Boolean} [options.isServer=false] Specifies whether to operate in
       *     client or server mode
       * @param {Number} [options.maxPayload=0] The maximum allowed message length
       * @param {Boolean} [options.skipUTF8Validation=false] Specifies whether or
       *     not to skip UTF-8 validation for text and close messages
       */
      constructor(options = {}) {
        super();
        this._allowSynchronousEvents = options.allowSynchronousEvents !== void 0 ? options.allowSynchronousEvents : true;
        this._binaryType = options.binaryType || BINARY_TYPES[0];
        this._extensions = options.extensions || {};
        this._isServer = !!options.isServer;
        this._maxPayload = options.maxPayload | 0;
        this._skipUTF8Validation = !!options.skipUTF8Validation;
        this[kWebSocket] = void 0;
        this._bufferedBytes = 0;
        this._buffers = [];
        this._compressed = false;
        this._payloadLength = 0;
        this._mask = void 0;
        this._fragmented = 0;
        this._masked = false;
        this._fin = false;
        this._opcode = 0;
        this._totalPayloadLength = 0;
        this._messageLength = 0;
        this._fragments = [];
        this._errored = false;
        this._loop = false;
        this._state = GET_INFO;
      }
      /**
       * Implements `Writable.prototype._write()`.
       *
       * @param {Buffer} chunk The chunk of data to write
       * @param {String} encoding The character encoding of `chunk`
       * @param {Function} cb Callback
       * @private
       */
      _write(chunk, encoding, cb) {
        if (this._opcode === 8 && this._state == GET_INFO) return cb();
        this._bufferedBytes += chunk.length;
        this._buffers.push(chunk);
        this.startLoop(cb);
      }
      /**
       * Consumes `n` bytes from the buffered data.
       *
       * @param {Number} n The number of bytes to consume
       * @return {Buffer} The consumed bytes
       * @private
       */
      consume(n) {
        this._bufferedBytes -= n;
        if (n === this._buffers[0].length) return this._buffers.shift();
        if (n < this._buffers[0].length) {
          const buf = this._buffers[0];
          this._buffers[0] = new FastBuffer(
            buf.buffer,
            buf.byteOffset + n,
            buf.length - n
          );
          return new FastBuffer(buf.buffer, buf.byteOffset, n);
        }
        const dst = Buffer.allocUnsafe(n);
        do {
          const buf = this._buffers[0];
          const offset = dst.length - n;
          if (n >= buf.length) {
            dst.set(this._buffers.shift(), offset);
          } else {
            dst.set(new Uint8Array(buf.buffer, buf.byteOffset, n), offset);
            this._buffers[0] = new FastBuffer(
              buf.buffer,
              buf.byteOffset + n,
              buf.length - n
            );
          }
          n -= buf.length;
        } while (n > 0);
        return dst;
      }
      /**
       * Starts the parsing loop.
       *
       * @param {Function} cb Callback
       * @private
       */
      startLoop(cb) {
        this._loop = true;
        do {
          switch (this._state) {
            case GET_INFO:
              this.getInfo(cb);
              break;
            case GET_PAYLOAD_LENGTH_16:
              this.getPayloadLength16(cb);
              break;
            case GET_PAYLOAD_LENGTH_64:
              this.getPayloadLength64(cb);
              break;
            case GET_MASK:
              this.getMask();
              break;
            case GET_DATA:
              this.getData(cb);
              break;
            case INFLATING:
            case DEFER_EVENT:
              this._loop = false;
              return;
          }
        } while (this._loop);
        if (!this._errored) cb();
      }
      /**
       * Reads the first two bytes of a frame.
       *
       * @param {Function} cb Callback
       * @private
       */
      getInfo(cb) {
        if (this._bufferedBytes < 2) {
          this._loop = false;
          return;
        }
        const buf = this.consume(2);
        if ((buf[0] & 48) !== 0) {
          const error = this.createError(
            RangeError,
            "RSV2 and RSV3 must be clear",
            true,
            1002,
            "WS_ERR_UNEXPECTED_RSV_2_3"
          );
          cb(error);
          return;
        }
        const compressed = (buf[0] & 64) === 64;
        if (compressed && !this._extensions[PerMessageDeflate.extensionName]) {
          const error = this.createError(
            RangeError,
            "RSV1 must be clear",
            true,
            1002,
            "WS_ERR_UNEXPECTED_RSV_1"
          );
          cb(error);
          return;
        }
        this._fin = (buf[0] & 128) === 128;
        this._opcode = buf[0] & 15;
        this._payloadLength = buf[1] & 127;
        if (this._opcode === 0) {
          if (compressed) {
            const error = this.createError(
              RangeError,
              "RSV1 must be clear",
              true,
              1002,
              "WS_ERR_UNEXPECTED_RSV_1"
            );
            cb(error);
            return;
          }
          if (!this._fragmented) {
            const error = this.createError(
              RangeError,
              "invalid opcode 0",
              true,
              1002,
              "WS_ERR_INVALID_OPCODE"
            );
            cb(error);
            return;
          }
          this._opcode = this._fragmented;
        } else if (this._opcode === 1 || this._opcode === 2) {
          if (this._fragmented) {
            const error = this.createError(
              RangeError,
              `invalid opcode ${this._opcode}`,
              true,
              1002,
              "WS_ERR_INVALID_OPCODE"
            );
            cb(error);
            return;
          }
          this._compressed = compressed;
        } else if (this._opcode > 7 && this._opcode < 11) {
          if (!this._fin) {
            const error = this.createError(
              RangeError,
              "FIN must be set",
              true,
              1002,
              "WS_ERR_EXPECTED_FIN"
            );
            cb(error);
            return;
          }
          if (compressed) {
            const error = this.createError(
              RangeError,
              "RSV1 must be clear",
              true,
              1002,
              "WS_ERR_UNEXPECTED_RSV_1"
            );
            cb(error);
            return;
          }
          if (this._payloadLength > 125 || this._opcode === 8 && this._payloadLength === 1) {
            const error = this.createError(
              RangeError,
              `invalid payload length ${this._payloadLength}`,
              true,
              1002,
              "WS_ERR_INVALID_CONTROL_PAYLOAD_LENGTH"
            );
            cb(error);
            return;
          }
        } else {
          const error = this.createError(
            RangeError,
            `invalid opcode ${this._opcode}`,
            true,
            1002,
            "WS_ERR_INVALID_OPCODE"
          );
          cb(error);
          return;
        }
        if (!this._fin && !this._fragmented) this._fragmented = this._opcode;
        this._masked = (buf[1] & 128) === 128;
        if (this._isServer) {
          if (!this._masked) {
            const error = this.createError(
              RangeError,
              "MASK must be set",
              true,
              1002,
              "WS_ERR_EXPECTED_MASK"
            );
            cb(error);
            return;
          }
        } else if (this._masked) {
          const error = this.createError(
            RangeError,
            "MASK must be clear",
            true,
            1002,
            "WS_ERR_UNEXPECTED_MASK"
          );
          cb(error);
          return;
        }
        if (this._payloadLength === 126) this._state = GET_PAYLOAD_LENGTH_16;
        else if (this._payloadLength === 127) this._state = GET_PAYLOAD_LENGTH_64;
        else this.haveLength(cb);
      }
      /**
       * Gets extended payload length (7+16).
       *
       * @param {Function} cb Callback
       * @private
       */
      getPayloadLength16(cb) {
        if (this._bufferedBytes < 2) {
          this._loop = false;
          return;
        }
        this._payloadLength = this.consume(2).readUInt16BE(0);
        this.haveLength(cb);
      }
      /**
       * Gets extended payload length (7+64).
       *
       * @param {Function} cb Callback
       * @private
       */
      getPayloadLength64(cb) {
        if (this._bufferedBytes < 8) {
          this._loop = false;
          return;
        }
        const buf = this.consume(8);
        const num = buf.readUInt32BE(0);
        if (num > Math.pow(2, 53 - 32) - 1) {
          const error = this.createError(
            RangeError,
            "Unsupported WebSocket frame: payload length > 2^53 - 1",
            false,
            1009,
            "WS_ERR_UNSUPPORTED_DATA_PAYLOAD_LENGTH"
          );
          cb(error);
          return;
        }
        this._payloadLength = num * Math.pow(2, 32) + buf.readUInt32BE(4);
        this.haveLength(cb);
      }
      /**
       * Payload length has been read.
       *
       * @param {Function} cb Callback
       * @private
       */
      haveLength(cb) {
        if (this._payloadLength && this._opcode < 8) {
          this._totalPayloadLength += this._payloadLength;
          if (this._totalPayloadLength > this._maxPayload && this._maxPayload > 0) {
            const error = this.createError(
              RangeError,
              "Max payload size exceeded",
              false,
              1009,
              "WS_ERR_UNSUPPORTED_MESSAGE_LENGTH"
            );
            cb(error);
            return;
          }
        }
        if (this._masked) this._state = GET_MASK;
        else this._state = GET_DATA;
      }
      /**
       * Reads mask bytes.
       *
       * @private
       */
      getMask() {
        if (this._bufferedBytes < 4) {
          this._loop = false;
          return;
        }
        this._mask = this.consume(4);
        this._state = GET_DATA;
      }
      /**
       * Reads data bytes.
       *
       * @param {Function} cb Callback
       * @private
       */
      getData(cb) {
        let data = EMPTY_BUFFER;
        if (this._payloadLength) {
          if (this._bufferedBytes < this._payloadLength) {
            this._loop = false;
            return;
          }
          data = this.consume(this._payloadLength);
          if (this._masked && (this._mask[0] | this._mask[1] | this._mask[2] | this._mask[3]) !== 0) {
            unmask(data, this._mask);
          }
        }
        if (this._opcode > 7) {
          this.controlMessage(data, cb);
          return;
        }
        if (this._compressed) {
          this._state = INFLATING;
          this.decompress(data, cb);
          return;
        }
        if (data.length) {
          this._messageLength = this._totalPayloadLength;
          this._fragments.push(data);
        }
        this.dataMessage(cb);
      }
      /**
       * Decompresses data.
       *
       * @param {Buffer} data Compressed data
       * @param {Function} cb Callback
       * @private
       */
      decompress(data, cb) {
        const perMessageDeflate = this._extensions[PerMessageDeflate.extensionName];
        perMessageDeflate.decompress(data, this._fin, (err, buf) => {
          if (err) return cb(err);
          if (buf.length) {
            this._messageLength += buf.length;
            if (this._messageLength > this._maxPayload && this._maxPayload > 0) {
              const error = this.createError(
                RangeError,
                "Max payload size exceeded",
                false,
                1009,
                "WS_ERR_UNSUPPORTED_MESSAGE_LENGTH"
              );
              cb(error);
              return;
            }
            this._fragments.push(buf);
          }
          this.dataMessage(cb);
          if (this._state === GET_INFO) this.startLoop(cb);
        });
      }
      /**
       * Handles a data message.
       *
       * @param {Function} cb Callback
       * @private
       */
      dataMessage(cb) {
        if (!this._fin) {
          this._state = GET_INFO;
          return;
        }
        const messageLength = this._messageLength;
        const fragments = this._fragments;
        this._totalPayloadLength = 0;
        this._messageLength = 0;
        this._fragmented = 0;
        this._fragments = [];
        if (this._opcode === 2) {
          let data;
          if (this._binaryType === "nodebuffer") {
            data = concat(fragments, messageLength);
          } else if (this._binaryType === "arraybuffer") {
            data = toArrayBuffer(concat(fragments, messageLength));
          } else if (this._binaryType === "blob") {
            data = new Blob(fragments);
          } else {
            data = fragments;
          }
          if (this._allowSynchronousEvents) {
            this.emit("message", data, true);
            this._state = GET_INFO;
          } else {
            this._state = DEFER_EVENT;
            setImmediate(() => {
              this.emit("message", data, true);
              this._state = GET_INFO;
              this.startLoop(cb);
            });
          }
        } else {
          const buf = concat(fragments, messageLength);
          if (!this._skipUTF8Validation && !isValidUTF8(buf)) {
            const error = this.createError(
              Error,
              "invalid UTF-8 sequence",
              true,
              1007,
              "WS_ERR_INVALID_UTF8"
            );
            cb(error);
            return;
          }
          if (this._state === INFLATING || this._allowSynchronousEvents) {
            this.emit("message", buf, false);
            this._state = GET_INFO;
          } else {
            this._state = DEFER_EVENT;
            setImmediate(() => {
              this.emit("message", buf, false);
              this._state = GET_INFO;
              this.startLoop(cb);
            });
          }
        }
      }
      /**
       * Handles a control message.
       *
       * @param {Buffer} data Data to handle
       * @return {(Error|RangeError|undefined)} A possible error
       * @private
       */
      controlMessage(data, cb) {
        if (this._opcode === 8) {
          if (data.length === 0) {
            this._loop = false;
            this.emit("conclude", 1005, EMPTY_BUFFER);
            this.end();
          } else {
            const code = data.readUInt16BE(0);
            if (!isValidStatusCode(code)) {
              const error = this.createError(
                RangeError,
                `invalid status code ${code}`,
                true,
                1002,
                "WS_ERR_INVALID_CLOSE_CODE"
              );
              cb(error);
              return;
            }
            const buf = new FastBuffer(
              data.buffer,
              data.byteOffset + 2,
              data.length - 2
            );
            if (!this._skipUTF8Validation && !isValidUTF8(buf)) {
              const error = this.createError(
                Error,
                "invalid UTF-8 sequence",
                true,
                1007,
                "WS_ERR_INVALID_UTF8"
              );
              cb(error);
              return;
            }
            this._loop = false;
            this.emit("conclude", code, buf);
            this.end();
          }
          this._state = GET_INFO;
          return;
        }
        if (this._allowSynchronousEvents) {
          this.emit(this._opcode === 9 ? "ping" : "pong", data);
          this._state = GET_INFO;
        } else {
          this._state = DEFER_EVENT;
          setImmediate(() => {
            this.emit(this._opcode === 9 ? "ping" : "pong", data);
            this._state = GET_INFO;
            this.startLoop(cb);
          });
        }
      }
      /**
       * Builds an error object.
       *
       * @param {function(new:Error|RangeError)} ErrorCtor The error constructor
       * @param {String} message The error message
       * @param {Boolean} prefix Specifies whether or not to add a default prefix to
       *     `message`
       * @param {Number} statusCode The status code
       * @param {String} errorCode The exposed error code
       * @return {(Error|RangeError)} The error
       * @private
       */
      createError(ErrorCtor, message, prefix, statusCode, errorCode) {
        this._loop = false;
        this._errored = true;
        const err = new ErrorCtor(
          prefix ? `Invalid WebSocket frame: ${message}` : message
        );
        Error.captureStackTrace(err, this.createError);
        err.code = errorCode;
        err[kStatusCode] = statusCode;
        return err;
      }
    };
    module2.exports = Receiver2;
  }
});

// ../../node_modules/.pnpm/ws@8.19.0/node_modules/ws/lib/sender.js
var require_sender = __commonJS({
  "../../node_modules/.pnpm/ws@8.19.0/node_modules/ws/lib/sender.js"(exports2, module2) {
    "use strict";
    var { Duplex } = require("stream");
    var { randomFillSync } = require("crypto");
    var PerMessageDeflate = require_permessage_deflate();
    var { EMPTY_BUFFER, kWebSocket, NOOP } = require_constants();
    var { isBlob, isValidStatusCode } = require_validation();
    var { mask: applyMask, toBuffer } = require_buffer_util();
    var kByteLength = Symbol("kByteLength");
    var maskBuffer = Buffer.alloc(4);
    var RANDOM_POOL_SIZE = 8 * 1024;
    var randomPool;
    var randomPoolPointer = RANDOM_POOL_SIZE;
    var DEFAULT = 0;
    var DEFLATING = 1;
    var GET_BLOB_DATA = 2;
    var Sender2 = class _Sender {
      /**
       * Creates a Sender instance.
       *
       * @param {Duplex} socket The connection socket
       * @param {Object} [extensions] An object containing the negotiated extensions
       * @param {Function} [generateMask] The function used to generate the masking
       *     key
       */
      constructor(socket, extensions, generateMask) {
        this._extensions = extensions || {};
        if (generateMask) {
          this._generateMask = generateMask;
          this._maskBuffer = Buffer.alloc(4);
        }
        this._socket = socket;
        this._firstFragment = true;
        this._compress = false;
        this._bufferedBytes = 0;
        this._queue = [];
        this._state = DEFAULT;
        this.onerror = NOOP;
        this[kWebSocket] = void 0;
      }
      /**
       * Frames a piece of data according to the HyBi WebSocket protocol.
       *
       * @param {(Buffer|String)} data The data to frame
       * @param {Object} options Options object
       * @param {Boolean} [options.fin=false] Specifies whether or not to set the
       *     FIN bit
       * @param {Function} [options.generateMask] The function used to generate the
       *     masking key
       * @param {Boolean} [options.mask=false] Specifies whether or not to mask
       *     `data`
       * @param {Buffer} [options.maskBuffer] The buffer used to store the masking
       *     key
       * @param {Number} options.opcode The opcode
       * @param {Boolean} [options.readOnly=false] Specifies whether `data` can be
       *     modified
       * @param {Boolean} [options.rsv1=false] Specifies whether or not to set the
       *     RSV1 bit
       * @return {(Buffer|String)[]} The framed data
       * @public
       */
      static frame(data, options) {
        let mask;
        let merge = false;
        let offset = 2;
        let skipMasking = false;
        if (options.mask) {
          mask = options.maskBuffer || maskBuffer;
          if (options.generateMask) {
            options.generateMask(mask);
          } else {
            if (randomPoolPointer === RANDOM_POOL_SIZE) {
              if (randomPool === void 0) {
                randomPool = Buffer.alloc(RANDOM_POOL_SIZE);
              }
              randomFillSync(randomPool, 0, RANDOM_POOL_SIZE);
              randomPoolPointer = 0;
            }
            mask[0] = randomPool[randomPoolPointer++];
            mask[1] = randomPool[randomPoolPointer++];
            mask[2] = randomPool[randomPoolPointer++];
            mask[3] = randomPool[randomPoolPointer++];
          }
          skipMasking = (mask[0] | mask[1] | mask[2] | mask[3]) === 0;
          offset = 6;
        }
        let dataLength;
        if (typeof data === "string") {
          if ((!options.mask || skipMasking) && options[kByteLength] !== void 0) {
            dataLength = options[kByteLength];
          } else {
            data = Buffer.from(data);
            dataLength = data.length;
          }
        } else {
          dataLength = data.length;
          merge = options.mask && options.readOnly && !skipMasking;
        }
        let payloadLength = dataLength;
        if (dataLength >= 65536) {
          offset += 8;
          payloadLength = 127;
        } else if (dataLength > 125) {
          offset += 2;
          payloadLength = 126;
        }
        const target = Buffer.allocUnsafe(merge ? dataLength + offset : offset);
        target[0] = options.fin ? options.opcode | 128 : options.opcode;
        if (options.rsv1) target[0] |= 64;
        target[1] = payloadLength;
        if (payloadLength === 126) {
          target.writeUInt16BE(dataLength, 2);
        } else if (payloadLength === 127) {
          target[2] = target[3] = 0;
          target.writeUIntBE(dataLength, 4, 6);
        }
        if (!options.mask) return [target, data];
        target[1] |= 128;
        target[offset - 4] = mask[0];
        target[offset - 3] = mask[1];
        target[offset - 2] = mask[2];
        target[offset - 1] = mask[3];
        if (skipMasking) return [target, data];
        if (merge) {
          applyMask(data, mask, target, offset, dataLength);
          return [target];
        }
        applyMask(data, mask, data, 0, dataLength);
        return [target, data];
      }
      /**
       * Sends a close message to the other peer.
       *
       * @param {Number} [code] The status code component of the body
       * @param {(String|Buffer)} [data] The message component of the body
       * @param {Boolean} [mask=false] Specifies whether or not to mask the message
       * @param {Function} [cb] Callback
       * @public
       */
      close(code, data, mask, cb) {
        let buf;
        if (code === void 0) {
          buf = EMPTY_BUFFER;
        } else if (typeof code !== "number" || !isValidStatusCode(code)) {
          throw new TypeError("First argument must be a valid error code number");
        } else if (data === void 0 || !data.length) {
          buf = Buffer.allocUnsafe(2);
          buf.writeUInt16BE(code, 0);
        } else {
          const length = Buffer.byteLength(data);
          if (length > 123) {
            throw new RangeError("The message must not be greater than 123 bytes");
          }
          buf = Buffer.allocUnsafe(2 + length);
          buf.writeUInt16BE(code, 0);
          if (typeof data === "string") {
            buf.write(data, 2);
          } else {
            buf.set(data, 2);
          }
        }
        const options = {
          [kByteLength]: buf.length,
          fin: true,
          generateMask: this._generateMask,
          mask,
          maskBuffer: this._maskBuffer,
          opcode: 8,
          readOnly: false,
          rsv1: false
        };
        if (this._state !== DEFAULT) {
          this.enqueue([this.dispatch, buf, false, options, cb]);
        } else {
          this.sendFrame(_Sender.frame(buf, options), cb);
        }
      }
      /**
       * Sends a ping message to the other peer.
       *
       * @param {*} data The message to send
       * @param {Boolean} [mask=false] Specifies whether or not to mask `data`
       * @param {Function} [cb] Callback
       * @public
       */
      ping(data, mask, cb) {
        let byteLength;
        let readOnly;
        if (typeof data === "string") {
          byteLength = Buffer.byteLength(data);
          readOnly = false;
        } else if (isBlob(data)) {
          byteLength = data.size;
          readOnly = false;
        } else {
          data = toBuffer(data);
          byteLength = data.length;
          readOnly = toBuffer.readOnly;
        }
        if (byteLength > 125) {
          throw new RangeError("The data size must not be greater than 125 bytes");
        }
        const options = {
          [kByteLength]: byteLength,
          fin: true,
          generateMask: this._generateMask,
          mask,
          maskBuffer: this._maskBuffer,
          opcode: 9,
          readOnly,
          rsv1: false
        };
        if (isBlob(data)) {
          if (this._state !== DEFAULT) {
            this.enqueue([this.getBlobData, data, false, options, cb]);
          } else {
            this.getBlobData(data, false, options, cb);
          }
        } else if (this._state !== DEFAULT) {
          this.enqueue([this.dispatch, data, false, options, cb]);
        } else {
          this.sendFrame(_Sender.frame(data, options), cb);
        }
      }
      /**
       * Sends a pong message to the other peer.
       *
       * @param {*} data The message to send
       * @param {Boolean} [mask=false] Specifies whether or not to mask `data`
       * @param {Function} [cb] Callback
       * @public
       */
      pong(data, mask, cb) {
        let byteLength;
        let readOnly;
        if (typeof data === "string") {
          byteLength = Buffer.byteLength(data);
          readOnly = false;
        } else if (isBlob(data)) {
          byteLength = data.size;
          readOnly = false;
        } else {
          data = toBuffer(data);
          byteLength = data.length;
          readOnly = toBuffer.readOnly;
        }
        if (byteLength > 125) {
          throw new RangeError("The data size must not be greater than 125 bytes");
        }
        const options = {
          [kByteLength]: byteLength,
          fin: true,
          generateMask: this._generateMask,
          mask,
          maskBuffer: this._maskBuffer,
          opcode: 10,
          readOnly,
          rsv1: false
        };
        if (isBlob(data)) {
          if (this._state !== DEFAULT) {
            this.enqueue([this.getBlobData, data, false, options, cb]);
          } else {
            this.getBlobData(data, false, options, cb);
          }
        } else if (this._state !== DEFAULT) {
          this.enqueue([this.dispatch, data, false, options, cb]);
        } else {
          this.sendFrame(_Sender.frame(data, options), cb);
        }
      }
      /**
       * Sends a data message to the other peer.
       *
       * @param {*} data The message to send
       * @param {Object} options Options object
       * @param {Boolean} [options.binary=false] Specifies whether `data` is binary
       *     or text
       * @param {Boolean} [options.compress=false] Specifies whether or not to
       *     compress `data`
       * @param {Boolean} [options.fin=false] Specifies whether the fragment is the
       *     last one
       * @param {Boolean} [options.mask=false] Specifies whether or not to mask
       *     `data`
       * @param {Function} [cb] Callback
       * @public
       */
      send(data, options, cb) {
        const perMessageDeflate = this._extensions[PerMessageDeflate.extensionName];
        let opcode = options.binary ? 2 : 1;
        let rsv1 = options.compress;
        let byteLength;
        let readOnly;
        if (typeof data === "string") {
          byteLength = Buffer.byteLength(data);
          readOnly = false;
        } else if (isBlob(data)) {
          byteLength = data.size;
          readOnly = false;
        } else {
          data = toBuffer(data);
          byteLength = data.length;
          readOnly = toBuffer.readOnly;
        }
        if (this._firstFragment) {
          this._firstFragment = false;
          if (rsv1 && perMessageDeflate && perMessageDeflate.params[perMessageDeflate._isServer ? "server_no_context_takeover" : "client_no_context_takeover"]) {
            rsv1 = byteLength >= perMessageDeflate._threshold;
          }
          this._compress = rsv1;
        } else {
          rsv1 = false;
          opcode = 0;
        }
        if (options.fin) this._firstFragment = true;
        const opts = {
          [kByteLength]: byteLength,
          fin: options.fin,
          generateMask: this._generateMask,
          mask: options.mask,
          maskBuffer: this._maskBuffer,
          opcode,
          readOnly,
          rsv1
        };
        if (isBlob(data)) {
          if (this._state !== DEFAULT) {
            this.enqueue([this.getBlobData, data, this._compress, opts, cb]);
          } else {
            this.getBlobData(data, this._compress, opts, cb);
          }
        } else if (this._state !== DEFAULT) {
          this.enqueue([this.dispatch, data, this._compress, opts, cb]);
        } else {
          this.dispatch(data, this._compress, opts, cb);
        }
      }
      /**
       * Gets the contents of a blob as binary data.
       *
       * @param {Blob} blob The blob
       * @param {Boolean} [compress=false] Specifies whether or not to compress
       *     the data
       * @param {Object} options Options object
       * @param {Boolean} [options.fin=false] Specifies whether or not to set the
       *     FIN bit
       * @param {Function} [options.generateMask] The function used to generate the
       *     masking key
       * @param {Boolean} [options.mask=false] Specifies whether or not to mask
       *     `data`
       * @param {Buffer} [options.maskBuffer] The buffer used to store the masking
       *     key
       * @param {Number} options.opcode The opcode
       * @param {Boolean} [options.readOnly=false] Specifies whether `data` can be
       *     modified
       * @param {Boolean} [options.rsv1=false] Specifies whether or not to set the
       *     RSV1 bit
       * @param {Function} [cb] Callback
       * @private
       */
      getBlobData(blob, compress, options, cb) {
        this._bufferedBytes += options[kByteLength];
        this._state = GET_BLOB_DATA;
        blob.arrayBuffer().then((arrayBuffer) => {
          if (this._socket.destroyed) {
            const err = new Error(
              "The socket was closed while the blob was being read"
            );
            process.nextTick(callCallbacks, this, err, cb);
            return;
          }
          this._bufferedBytes -= options[kByteLength];
          const data = toBuffer(arrayBuffer);
          if (!compress) {
            this._state = DEFAULT;
            this.sendFrame(_Sender.frame(data, options), cb);
            this.dequeue();
          } else {
            this.dispatch(data, compress, options, cb);
          }
        }).catch((err) => {
          process.nextTick(onError, this, err, cb);
        });
      }
      /**
       * Dispatches a message.
       *
       * @param {(Buffer|String)} data The message to send
       * @param {Boolean} [compress=false] Specifies whether or not to compress
       *     `data`
       * @param {Object} options Options object
       * @param {Boolean} [options.fin=false] Specifies whether or not to set the
       *     FIN bit
       * @param {Function} [options.generateMask] The function used to generate the
       *     masking key
       * @param {Boolean} [options.mask=false] Specifies whether or not to mask
       *     `data`
       * @param {Buffer} [options.maskBuffer] The buffer used to store the masking
       *     key
       * @param {Number} options.opcode The opcode
       * @param {Boolean} [options.readOnly=false] Specifies whether `data` can be
       *     modified
       * @param {Boolean} [options.rsv1=false] Specifies whether or not to set the
       *     RSV1 bit
       * @param {Function} [cb] Callback
       * @private
       */
      dispatch(data, compress, options, cb) {
        if (!compress) {
          this.sendFrame(_Sender.frame(data, options), cb);
          return;
        }
        const perMessageDeflate = this._extensions[PerMessageDeflate.extensionName];
        this._bufferedBytes += options[kByteLength];
        this._state = DEFLATING;
        perMessageDeflate.compress(data, options.fin, (_, buf) => {
          if (this._socket.destroyed) {
            const err = new Error(
              "The socket was closed while data was being compressed"
            );
            callCallbacks(this, err, cb);
            return;
          }
          this._bufferedBytes -= options[kByteLength];
          this._state = DEFAULT;
          options.readOnly = false;
          this.sendFrame(_Sender.frame(buf, options), cb);
          this.dequeue();
        });
      }
      /**
       * Executes queued send operations.
       *
       * @private
       */
      dequeue() {
        while (this._state === DEFAULT && this._queue.length) {
          const params = this._queue.shift();
          this._bufferedBytes -= params[3][kByteLength];
          Reflect.apply(params[0], this, params.slice(1));
        }
      }
      /**
       * Enqueues a send operation.
       *
       * @param {Array} params Send operation parameters.
       * @private
       */
      enqueue(params) {
        this._bufferedBytes += params[3][kByteLength];
        this._queue.push(params);
      }
      /**
       * Sends a frame.
       *
       * @param {(Buffer | String)[]} list The frame to send
       * @param {Function} [cb] Callback
       * @private
       */
      sendFrame(list, cb) {
        if (list.length === 2) {
          this._socket.cork();
          this._socket.write(list[0]);
          this._socket.write(list[1], cb);
          this._socket.uncork();
        } else {
          this._socket.write(list[0], cb);
        }
      }
    };
    module2.exports = Sender2;
    function callCallbacks(sender, err, cb) {
      if (typeof cb === "function") cb(err);
      for (let i = 0; i < sender._queue.length; i++) {
        const params = sender._queue[i];
        const callback = params[params.length - 1];
        if (typeof callback === "function") callback(err);
      }
    }
    function onError(sender, err, cb) {
      callCallbacks(sender, err, cb);
      sender.onerror(err);
    }
  }
});

// ../../node_modules/.pnpm/ws@8.19.0/node_modules/ws/lib/event-target.js
var require_event_target = __commonJS({
  "../../node_modules/.pnpm/ws@8.19.0/node_modules/ws/lib/event-target.js"(exports2, module2) {
    "use strict";
    var { kForOnEventAttribute, kListener } = require_constants();
    var kCode = Symbol("kCode");
    var kData = Symbol("kData");
    var kError = Symbol("kError");
    var kMessage = Symbol("kMessage");
    var kReason = Symbol("kReason");
    var kTarget = Symbol("kTarget");
    var kType = Symbol("kType");
    var kWasClean = Symbol("kWasClean");
    var Event = class {
      /**
       * Create a new `Event`.
       *
       * @param {String} type The name of the event
       * @throws {TypeError} If the `type` argument is not specified
       */
      constructor(type) {
        this[kTarget] = null;
        this[kType] = type;
      }
      /**
       * @type {*}
       */
      get target() {
        return this[kTarget];
      }
      /**
       * @type {String}
       */
      get type() {
        return this[kType];
      }
    };
    Object.defineProperty(Event.prototype, "target", { enumerable: true });
    Object.defineProperty(Event.prototype, "type", { enumerable: true });
    var CloseEvent = class extends Event {
      /**
       * Create a new `CloseEvent`.
       *
       * @param {String} type The name of the event
       * @param {Object} [options] A dictionary object that allows for setting
       *     attributes via object members of the same name
       * @param {Number} [options.code=0] The status code explaining why the
       *     connection was closed
       * @param {String} [options.reason=''] A human-readable string explaining why
       *     the connection was closed
       * @param {Boolean} [options.wasClean=false] Indicates whether or not the
       *     connection was cleanly closed
       */
      constructor(type, options = {}) {
        super(type);
        this[kCode] = options.code === void 0 ? 0 : options.code;
        this[kReason] = options.reason === void 0 ? "" : options.reason;
        this[kWasClean] = options.wasClean === void 0 ? false : options.wasClean;
      }
      /**
       * @type {Number}
       */
      get code() {
        return this[kCode];
      }
      /**
       * @type {String}
       */
      get reason() {
        return this[kReason];
      }
      /**
       * @type {Boolean}
       */
      get wasClean() {
        return this[kWasClean];
      }
    };
    Object.defineProperty(CloseEvent.prototype, "code", { enumerable: true });
    Object.defineProperty(CloseEvent.prototype, "reason", { enumerable: true });
    Object.defineProperty(CloseEvent.prototype, "wasClean", { enumerable: true });
    var ErrorEvent = class extends Event {
      /**
       * Create a new `ErrorEvent`.
       *
       * @param {String} type The name of the event
       * @param {Object} [options] A dictionary object that allows for setting
       *     attributes via object members of the same name
       * @param {*} [options.error=null] The error that generated this event
       * @param {String} [options.message=''] The error message
       */
      constructor(type, options = {}) {
        super(type);
        this[kError] = options.error === void 0 ? null : options.error;
        this[kMessage] = options.message === void 0 ? "" : options.message;
      }
      /**
       * @type {*}
       */
      get error() {
        return this[kError];
      }
      /**
       * @type {String}
       */
      get message() {
        return this[kMessage];
      }
    };
    Object.defineProperty(ErrorEvent.prototype, "error", { enumerable: true });
    Object.defineProperty(ErrorEvent.prototype, "message", { enumerable: true });
    var MessageEvent = class extends Event {
      /**
       * Create a new `MessageEvent`.
       *
       * @param {String} type The name of the event
       * @param {Object} [options] A dictionary object that allows for setting
       *     attributes via object members of the same name
       * @param {*} [options.data=null] The message content
       */
      constructor(type, options = {}) {
        super(type);
        this[kData] = options.data === void 0 ? null : options.data;
      }
      /**
       * @type {*}
       */
      get data() {
        return this[kData];
      }
    };
    Object.defineProperty(MessageEvent.prototype, "data", { enumerable: true });
    var EventTarget = {
      /**
       * Register an event listener.
       *
       * @param {String} type A string representing the event type to listen for
       * @param {(Function|Object)} handler The listener to add
       * @param {Object} [options] An options object specifies characteristics about
       *     the event listener
       * @param {Boolean} [options.once=false] A `Boolean` indicating that the
       *     listener should be invoked at most once after being added. If `true`,
       *     the listener would be automatically removed when invoked.
       * @public
       */
      addEventListener(type, handler, options = {}) {
        for (const listener of this.listeners(type)) {
          if (!options[kForOnEventAttribute] && listener[kListener] === handler && !listener[kForOnEventAttribute]) {
            return;
          }
        }
        let wrapper;
        if (type === "message") {
          wrapper = function onMessage(data, isBinary) {
            const event = new MessageEvent("message", {
              data: isBinary ? data : data.toString()
            });
            event[kTarget] = this;
            callListener(handler, this, event);
          };
        } else if (type === "close") {
          wrapper = function onClose(code, message) {
            const event = new CloseEvent("close", {
              code,
              reason: message.toString(),
              wasClean: this._closeFrameReceived && this._closeFrameSent
            });
            event[kTarget] = this;
            callListener(handler, this, event);
          };
        } else if (type === "error") {
          wrapper = function onError(error) {
            const event = new ErrorEvent("error", {
              error,
              message: error.message
            });
            event[kTarget] = this;
            callListener(handler, this, event);
          };
        } else if (type === "open") {
          wrapper = function onOpen() {
            const event = new Event("open");
            event[kTarget] = this;
            callListener(handler, this, event);
          };
        } else {
          return;
        }
        wrapper[kForOnEventAttribute] = !!options[kForOnEventAttribute];
        wrapper[kListener] = handler;
        if (options.once) {
          this.once(type, wrapper);
        } else {
          this.on(type, wrapper);
        }
      },
      /**
       * Remove an event listener.
       *
       * @param {String} type A string representing the event type to remove
       * @param {(Function|Object)} handler The listener to remove
       * @public
       */
      removeEventListener(type, handler) {
        for (const listener of this.listeners(type)) {
          if (listener[kListener] === handler && !listener[kForOnEventAttribute]) {
            this.removeListener(type, listener);
            break;
          }
        }
      }
    };
    module2.exports = {
      CloseEvent,
      ErrorEvent,
      Event,
      EventTarget,
      MessageEvent
    };
    function callListener(listener, thisArg, event) {
      if (typeof listener === "object" && listener.handleEvent) {
        listener.handleEvent.call(listener, event);
      } else {
        listener.call(thisArg, event);
      }
    }
  }
});

// ../../node_modules/.pnpm/ws@8.19.0/node_modules/ws/lib/extension.js
var require_extension = __commonJS({
  "../../node_modules/.pnpm/ws@8.19.0/node_modules/ws/lib/extension.js"(exports2, module2) {
    "use strict";
    var { tokenChars } = require_validation();
    function push(dest, name, elem) {
      if (dest[name] === void 0) dest[name] = [elem];
      else dest[name].push(elem);
    }
    function parse(header) {
      const offers = /* @__PURE__ */ Object.create(null);
      let params = /* @__PURE__ */ Object.create(null);
      let mustUnescape = false;
      let isEscaping = false;
      let inQuotes = false;
      let extensionName;
      let paramName;
      let start = -1;
      let code = -1;
      let end = -1;
      let i = 0;
      for (; i < header.length; i++) {
        code = header.charCodeAt(i);
        if (extensionName === void 0) {
          if (end === -1 && tokenChars[code] === 1) {
            if (start === -1) start = i;
          } else if (i !== 0 && (code === 32 || code === 9)) {
            if (end === -1 && start !== -1) end = i;
          } else if (code === 59 || code === 44) {
            if (start === -1) {
              throw new SyntaxError(`Unexpected character at index ${i}`);
            }
            if (end === -1) end = i;
            const name = header.slice(start, end);
            if (code === 44) {
              push(offers, name, params);
              params = /* @__PURE__ */ Object.create(null);
            } else {
              extensionName = name;
            }
            start = end = -1;
          } else {
            throw new SyntaxError(`Unexpected character at index ${i}`);
          }
        } else if (paramName === void 0) {
          if (end === -1 && tokenChars[code] === 1) {
            if (start === -1) start = i;
          } else if (code === 32 || code === 9) {
            if (end === -1 && start !== -1) end = i;
          } else if (code === 59 || code === 44) {
            if (start === -1) {
              throw new SyntaxError(`Unexpected character at index ${i}`);
            }
            if (end === -1) end = i;
            push(params, header.slice(start, end), true);
            if (code === 44) {
              push(offers, extensionName, params);
              params = /* @__PURE__ */ Object.create(null);
              extensionName = void 0;
            }
            start = end = -1;
          } else if (code === 61 && start !== -1 && end === -1) {
            paramName = header.slice(start, i);
            start = end = -1;
          } else {
            throw new SyntaxError(`Unexpected character at index ${i}`);
          }
        } else {
          if (isEscaping) {
            if (tokenChars[code] !== 1) {
              throw new SyntaxError(`Unexpected character at index ${i}`);
            }
            if (start === -1) start = i;
            else if (!mustUnescape) mustUnescape = true;
            isEscaping = false;
          } else if (inQuotes) {
            if (tokenChars[code] === 1) {
              if (start === -1) start = i;
            } else if (code === 34 && start !== -1) {
              inQuotes = false;
              end = i;
            } else if (code === 92) {
              isEscaping = true;
            } else {
              throw new SyntaxError(`Unexpected character at index ${i}`);
            }
          } else if (code === 34 && header.charCodeAt(i - 1) === 61) {
            inQuotes = true;
          } else if (end === -1 && tokenChars[code] === 1) {
            if (start === -1) start = i;
          } else if (start !== -1 && (code === 32 || code === 9)) {
            if (end === -1) end = i;
          } else if (code === 59 || code === 44) {
            if (start === -1) {
              throw new SyntaxError(`Unexpected character at index ${i}`);
            }
            if (end === -1) end = i;
            let value = header.slice(start, end);
            if (mustUnescape) {
              value = value.replace(/\\/g, "");
              mustUnescape = false;
            }
            push(params, paramName, value);
            if (code === 44) {
              push(offers, extensionName, params);
              params = /* @__PURE__ */ Object.create(null);
              extensionName = void 0;
            }
            paramName = void 0;
            start = end = -1;
          } else {
            throw new SyntaxError(`Unexpected character at index ${i}`);
          }
        }
      }
      if (start === -1 || inQuotes || code === 32 || code === 9) {
        throw new SyntaxError("Unexpected end of input");
      }
      if (end === -1) end = i;
      const token = header.slice(start, end);
      if (extensionName === void 0) {
        push(offers, token, params);
      } else {
        if (paramName === void 0) {
          push(params, token, true);
        } else if (mustUnescape) {
          push(params, paramName, token.replace(/\\/g, ""));
        } else {
          push(params, paramName, token);
        }
        push(offers, extensionName, params);
      }
      return offers;
    }
    function format(extensions) {
      return Object.keys(extensions).map((extension) => {
        let configurations = extensions[extension];
        if (!Array.isArray(configurations)) configurations = [configurations];
        return configurations.map((params) => {
          return [extension].concat(
            Object.keys(params).map((k) => {
              let values = params[k];
              if (!Array.isArray(values)) values = [values];
              return values.map((v) => v === true ? k : `${k}=${v}`).join("; ");
            })
          ).join("; ");
        }).join(", ");
      }).join(", ");
    }
    module2.exports = { format, parse };
  }
});

// ../../node_modules/.pnpm/ws@8.19.0/node_modules/ws/lib/websocket.js
var require_websocket = __commonJS({
  "../../node_modules/.pnpm/ws@8.19.0/node_modules/ws/lib/websocket.js"(exports2, module2) {
    "use strict";
    var EventEmitter = require("events");
    var https = require("https");
    var http2 = require("http");
    var net2 = require("net");
    var tls = require("tls");
    var { randomBytes, createHash } = require("crypto");
    var { Duplex, Readable: Readable2 } = require("stream");
    var { URL: URL3 } = require("url");
    var PerMessageDeflate = require_permessage_deflate();
    var Receiver2 = require_receiver();
    var Sender2 = require_sender();
    var { isBlob } = require_validation();
    var {
      BINARY_TYPES,
      CLOSE_TIMEOUT,
      EMPTY_BUFFER,
      GUID,
      kForOnEventAttribute,
      kListener,
      kStatusCode,
      kWebSocket,
      NOOP
    } = require_constants();
    var {
      EventTarget: { addEventListener: addEventListener2, removeEventListener }
    } = require_event_target();
    var { format, parse } = require_extension();
    var { toBuffer } = require_buffer_util();
    var kAborted = Symbol("kAborted");
    var protocolVersions = [8, 13];
    var readyStates = ["CONNECTING", "OPEN", "CLOSING", "CLOSED"];
    var subprotocolRegex = /^[!#$%&'*+\-.0-9A-Z^_`|a-z~]+$/;
    var WebSocket2 = class _WebSocket extends EventEmitter {
      /**
       * Create a new `WebSocket`.
       *
       * @param {(String|URL)} address The URL to which to connect
       * @param {(String|String[])} [protocols] The subprotocols
       * @param {Object} [options] Connection options
       */
      constructor(address, protocols, options) {
        super();
        this._binaryType = BINARY_TYPES[0];
        this._closeCode = 1006;
        this._closeFrameReceived = false;
        this._closeFrameSent = false;
        this._closeMessage = EMPTY_BUFFER;
        this._closeTimer = null;
        this._errorEmitted = false;
        this._extensions = {};
        this._paused = false;
        this._protocol = "";
        this._readyState = _WebSocket.CONNECTING;
        this._receiver = null;
        this._sender = null;
        this._socket = null;
        if (address !== null) {
          this._bufferedAmount = 0;
          this._isServer = false;
          this._redirects = 0;
          if (protocols === void 0) {
            protocols = [];
          } else if (!Array.isArray(protocols)) {
            if (typeof protocols === "object" && protocols !== null) {
              options = protocols;
              protocols = [];
            } else {
              protocols = [protocols];
            }
          }
          initAsClient(this, address, protocols, options);
        } else {
          this._autoPong = options.autoPong;
          this._closeTimeout = options.closeTimeout;
          this._isServer = true;
        }
      }
      /**
       * For historical reasons, the custom "nodebuffer" type is used by the default
       * instead of "blob".
       *
       * @type {String}
       */
      get binaryType() {
        return this._binaryType;
      }
      set binaryType(type) {
        if (!BINARY_TYPES.includes(type)) return;
        this._binaryType = type;
        if (this._receiver) this._receiver._binaryType = type;
      }
      /**
       * @type {Number}
       */
      get bufferedAmount() {
        if (!this._socket) return this._bufferedAmount;
        return this._socket._writableState.length + this._sender._bufferedBytes;
      }
      /**
       * @type {String}
       */
      get extensions() {
        return Object.keys(this._extensions).join();
      }
      /**
       * @type {Boolean}
       */
      get isPaused() {
        return this._paused;
      }
      /**
       * @type {Function}
       */
      /* istanbul ignore next */
      get onclose() {
        return null;
      }
      /**
       * @type {Function}
       */
      /* istanbul ignore next */
      get onerror() {
        return null;
      }
      /**
       * @type {Function}
       */
      /* istanbul ignore next */
      get onopen() {
        return null;
      }
      /**
       * @type {Function}
       */
      /* istanbul ignore next */
      get onmessage() {
        return null;
      }
      /**
       * @type {String}
       */
      get protocol() {
        return this._protocol;
      }
      /**
       * @type {Number}
       */
      get readyState() {
        return this._readyState;
      }
      /**
       * @type {String}
       */
      get url() {
        return this._url;
      }
      /**
       * Set up the socket and the internal resources.
       *
       * @param {Duplex} socket The network socket between the server and client
       * @param {Buffer} head The first packet of the upgraded stream
       * @param {Object} options Options object
       * @param {Boolean} [options.allowSynchronousEvents=false] Specifies whether
       *     any of the `'message'`, `'ping'`, and `'pong'` events can be emitted
       *     multiple times in the same tick
       * @param {Function} [options.generateMask] The function used to generate the
       *     masking key
       * @param {Number} [options.maxPayload=0] The maximum allowed message size
       * @param {Boolean} [options.skipUTF8Validation=false] Specifies whether or
       *     not to skip UTF-8 validation for text and close messages
       * @private
       */
      setSocket(socket, head, options) {
        const receiver = new Receiver2({
          allowSynchronousEvents: options.allowSynchronousEvents,
          binaryType: this.binaryType,
          extensions: this._extensions,
          isServer: this._isServer,
          maxPayload: options.maxPayload,
          skipUTF8Validation: options.skipUTF8Validation
        });
        const sender = new Sender2(socket, this._extensions, options.generateMask);
        this._receiver = receiver;
        this._sender = sender;
        this._socket = socket;
        receiver[kWebSocket] = this;
        sender[kWebSocket] = this;
        socket[kWebSocket] = this;
        receiver.on("conclude", receiverOnConclude);
        receiver.on("drain", receiverOnDrain);
        receiver.on("error", receiverOnError);
        receiver.on("message", receiverOnMessage);
        receiver.on("ping", receiverOnPing);
        receiver.on("pong", receiverOnPong);
        sender.onerror = senderOnError;
        if (socket.setTimeout) socket.setTimeout(0);
        if (socket.setNoDelay) socket.setNoDelay();
        if (head.length > 0) socket.unshift(head);
        socket.on("close", socketOnClose);
        socket.on("data", socketOnData);
        socket.on("end", socketOnEnd);
        socket.on("error", socketOnError);
        this._readyState = _WebSocket.OPEN;
        this.emit("open");
      }
      /**
       * Emit the `'close'` event.
       *
       * @private
       */
      emitClose() {
        if (!this._socket) {
          this._readyState = _WebSocket.CLOSED;
          this.emit("close", this._closeCode, this._closeMessage);
          return;
        }
        if (this._extensions[PerMessageDeflate.extensionName]) {
          this._extensions[PerMessageDeflate.extensionName].cleanup();
        }
        this._receiver.removeAllListeners();
        this._readyState = _WebSocket.CLOSED;
        this.emit("close", this._closeCode, this._closeMessage);
      }
      /**
       * Start a closing handshake.
       *
       *          +----------+   +-----------+   +----------+
       *     - - -|ws.close()|-->|close frame|-->|ws.close()|- - -
       *    |     +----------+   +-----------+   +----------+     |
       *          +----------+   +-----------+         |
       * CLOSING  |ws.close()|<--|close frame|<--+-----+       CLOSING
       *          +----------+   +-----------+   |
       *    |           |                        |   +---+        |
       *                +------------------------+-->|fin| - - - -
       *    |         +---+                      |   +---+
       *     - - - - -|fin|<---------------------+
       *              +---+
       *
       * @param {Number} [code] Status code explaining why the connection is closing
       * @param {(String|Buffer)} [data] The reason why the connection is
       *     closing
       * @public
       */
      close(code, data) {
        if (this.readyState === _WebSocket.CLOSED) return;
        if (this.readyState === _WebSocket.CONNECTING) {
          const msg = "WebSocket was closed before the connection was established";
          abortHandshake(this, this._req, msg);
          return;
        }
        if (this.readyState === _WebSocket.CLOSING) {
          if (this._closeFrameSent && (this._closeFrameReceived || this._receiver._writableState.errorEmitted)) {
            this._socket.end();
          }
          return;
        }
        this._readyState = _WebSocket.CLOSING;
        this._sender.close(code, data, !this._isServer, (err) => {
          if (err) return;
          this._closeFrameSent = true;
          if (this._closeFrameReceived || this._receiver._writableState.errorEmitted) {
            this._socket.end();
          }
        });
        setCloseTimer(this);
      }
      /**
       * Pause the socket.
       *
       * @public
       */
      pause() {
        if (this.readyState === _WebSocket.CONNECTING || this.readyState === _WebSocket.CLOSED) {
          return;
        }
        this._paused = true;
        this._socket.pause();
      }
      /**
       * Send a ping.
       *
       * @param {*} [data] The data to send
       * @param {Boolean} [mask] Indicates whether or not to mask `data`
       * @param {Function} [cb] Callback which is executed when the ping is sent
       * @public
       */
      ping(data, mask, cb) {
        if (this.readyState === _WebSocket.CONNECTING) {
          throw new Error("WebSocket is not open: readyState 0 (CONNECTING)");
        }
        if (typeof data === "function") {
          cb = data;
          data = mask = void 0;
        } else if (typeof mask === "function") {
          cb = mask;
          mask = void 0;
        }
        if (typeof data === "number") data = data.toString();
        if (this.readyState !== _WebSocket.OPEN) {
          sendAfterClose(this, data, cb);
          return;
        }
        if (mask === void 0) mask = !this._isServer;
        this._sender.ping(data || EMPTY_BUFFER, mask, cb);
      }
      /**
       * Send a pong.
       *
       * @param {*} [data] The data to send
       * @param {Boolean} [mask] Indicates whether or not to mask `data`
       * @param {Function} [cb] Callback which is executed when the pong is sent
       * @public
       */
      pong(data, mask, cb) {
        if (this.readyState === _WebSocket.CONNECTING) {
          throw new Error("WebSocket is not open: readyState 0 (CONNECTING)");
        }
        if (typeof data === "function") {
          cb = data;
          data = mask = void 0;
        } else if (typeof mask === "function") {
          cb = mask;
          mask = void 0;
        }
        if (typeof data === "number") data = data.toString();
        if (this.readyState !== _WebSocket.OPEN) {
          sendAfterClose(this, data, cb);
          return;
        }
        if (mask === void 0) mask = !this._isServer;
        this._sender.pong(data || EMPTY_BUFFER, mask, cb);
      }
      /**
       * Resume the socket.
       *
       * @public
       */
      resume() {
        if (this.readyState === _WebSocket.CONNECTING || this.readyState === _WebSocket.CLOSED) {
          return;
        }
        this._paused = false;
        if (!this._receiver._writableState.needDrain) this._socket.resume();
      }
      /**
       * Send a data message.
       *
       * @param {*} data The message to send
       * @param {Object} [options] Options object
       * @param {Boolean} [options.binary] Specifies whether `data` is binary or
       *     text
       * @param {Boolean} [options.compress] Specifies whether or not to compress
       *     `data`
       * @param {Boolean} [options.fin=true] Specifies whether the fragment is the
       *     last one
       * @param {Boolean} [options.mask] Specifies whether or not to mask `data`
       * @param {Function} [cb] Callback which is executed when data is written out
       * @public
       */
      send(data, options, cb) {
        if (this.readyState === _WebSocket.CONNECTING) {
          throw new Error("WebSocket is not open: readyState 0 (CONNECTING)");
        }
        if (typeof options === "function") {
          cb = options;
          options = {};
        }
        if (typeof data === "number") data = data.toString();
        if (this.readyState !== _WebSocket.OPEN) {
          sendAfterClose(this, data, cb);
          return;
        }
        const opts = {
          binary: typeof data !== "string",
          mask: !this._isServer,
          compress: true,
          fin: true,
          ...options
        };
        if (!this._extensions[PerMessageDeflate.extensionName]) {
          opts.compress = false;
        }
        this._sender.send(data || EMPTY_BUFFER, opts, cb);
      }
      /**
       * Forcibly close the connection.
       *
       * @public
       */
      terminate() {
        if (this.readyState === _WebSocket.CLOSED) return;
        if (this.readyState === _WebSocket.CONNECTING) {
          const msg = "WebSocket was closed before the connection was established";
          abortHandshake(this, this._req, msg);
          return;
        }
        if (this._socket) {
          this._readyState = _WebSocket.CLOSING;
          this._socket.destroy();
        }
      }
    };
    Object.defineProperty(WebSocket2, "CONNECTING", {
      enumerable: true,
      value: readyStates.indexOf("CONNECTING")
    });
    Object.defineProperty(WebSocket2.prototype, "CONNECTING", {
      enumerable: true,
      value: readyStates.indexOf("CONNECTING")
    });
    Object.defineProperty(WebSocket2, "OPEN", {
      enumerable: true,
      value: readyStates.indexOf("OPEN")
    });
    Object.defineProperty(WebSocket2.prototype, "OPEN", {
      enumerable: true,
      value: readyStates.indexOf("OPEN")
    });
    Object.defineProperty(WebSocket2, "CLOSING", {
      enumerable: true,
      value: readyStates.indexOf("CLOSING")
    });
    Object.defineProperty(WebSocket2.prototype, "CLOSING", {
      enumerable: true,
      value: readyStates.indexOf("CLOSING")
    });
    Object.defineProperty(WebSocket2, "CLOSED", {
      enumerable: true,
      value: readyStates.indexOf("CLOSED")
    });
    Object.defineProperty(WebSocket2.prototype, "CLOSED", {
      enumerable: true,
      value: readyStates.indexOf("CLOSED")
    });
    [
      "binaryType",
      "bufferedAmount",
      "extensions",
      "isPaused",
      "protocol",
      "readyState",
      "url"
    ].forEach((property) => {
      Object.defineProperty(WebSocket2.prototype, property, { enumerable: true });
    });
    ["open", "error", "close", "message"].forEach((method) => {
      Object.defineProperty(WebSocket2.prototype, `on${method}`, {
        enumerable: true,
        get() {
          for (const listener of this.listeners(method)) {
            if (listener[kForOnEventAttribute]) return listener[kListener];
          }
          return null;
        },
        set(handler) {
          for (const listener of this.listeners(method)) {
            if (listener[kForOnEventAttribute]) {
              this.removeListener(method, listener);
              break;
            }
          }
          if (typeof handler !== "function") return;
          this.addEventListener(method, handler, {
            [kForOnEventAttribute]: true
          });
        }
      });
    });
    WebSocket2.prototype.addEventListener = addEventListener2;
    WebSocket2.prototype.removeEventListener = removeEventListener;
    module2.exports = WebSocket2;
    function initAsClient(websocket, address, protocols, options) {
      const opts = {
        allowSynchronousEvents: true,
        autoPong: true,
        closeTimeout: CLOSE_TIMEOUT,
        protocolVersion: protocolVersions[1],
        maxPayload: 100 * 1024 * 1024,
        skipUTF8Validation: false,
        perMessageDeflate: true,
        followRedirects: false,
        maxRedirects: 10,
        ...options,
        socketPath: void 0,
        hostname: void 0,
        protocol: void 0,
        timeout: void 0,
        method: "GET",
        host: void 0,
        path: void 0,
        port: void 0
      };
      websocket._autoPong = opts.autoPong;
      websocket._closeTimeout = opts.closeTimeout;
      if (!protocolVersions.includes(opts.protocolVersion)) {
        throw new RangeError(
          `Unsupported protocol version: ${opts.protocolVersion} (supported versions: ${protocolVersions.join(", ")})`
        );
      }
      let parsedUrl;
      if (address instanceof URL3) {
        parsedUrl = address;
      } else {
        try {
          parsedUrl = new URL3(address);
        } catch (e) {
          throw new SyntaxError(`Invalid URL: ${address}`);
        }
      }
      if (parsedUrl.protocol === "http:") {
        parsedUrl.protocol = "ws:";
      } else if (parsedUrl.protocol === "https:") {
        parsedUrl.protocol = "wss:";
      }
      websocket._url = parsedUrl.href;
      const isSecure = parsedUrl.protocol === "wss:";
      const isIpcUrl = parsedUrl.protocol === "ws+unix:";
      let invalidUrlMessage;
      if (parsedUrl.protocol !== "ws:" && !isSecure && !isIpcUrl) {
        invalidUrlMessage = `The URL's protocol must be one of "ws:", "wss:", "http:", "https:", or "ws+unix:"`;
      } else if (isIpcUrl && !parsedUrl.pathname) {
        invalidUrlMessage = "The URL's pathname is empty";
      } else if (parsedUrl.hash) {
        invalidUrlMessage = "The URL contains a fragment identifier";
      }
      if (invalidUrlMessage) {
        const err = new SyntaxError(invalidUrlMessage);
        if (websocket._redirects === 0) {
          throw err;
        } else {
          emitErrorAndClose(websocket, err);
          return;
        }
      }
      const defaultPort = isSecure ? 443 : 80;
      const key = randomBytes(16).toString("base64");
      const request = isSecure ? https.request : http2.request;
      const protocolSet = /* @__PURE__ */ new Set();
      let perMessageDeflate;
      opts.createConnection = opts.createConnection || (isSecure ? tlsConnect : netConnect);
      opts.defaultPort = opts.defaultPort || defaultPort;
      opts.port = parsedUrl.port || defaultPort;
      opts.host = parsedUrl.hostname.startsWith("[") ? parsedUrl.hostname.slice(1, -1) : parsedUrl.hostname;
      opts.headers = {
        ...opts.headers,
        "Sec-WebSocket-Version": opts.protocolVersion,
        "Sec-WebSocket-Key": key,
        Connection: "Upgrade",
        Upgrade: "websocket"
      };
      opts.path = parsedUrl.pathname + parsedUrl.search;
      opts.timeout = opts.handshakeTimeout;
      if (opts.perMessageDeflate) {
        perMessageDeflate = new PerMessageDeflate(
          opts.perMessageDeflate !== true ? opts.perMessageDeflate : {},
          false,
          opts.maxPayload
        );
        opts.headers["Sec-WebSocket-Extensions"] = format({
          [PerMessageDeflate.extensionName]: perMessageDeflate.offer()
        });
      }
      if (protocols.length) {
        for (const protocol of protocols) {
          if (typeof protocol !== "string" || !subprotocolRegex.test(protocol) || protocolSet.has(protocol)) {
            throw new SyntaxError(
              "An invalid or duplicated subprotocol was specified"
            );
          }
          protocolSet.add(protocol);
        }
        opts.headers["Sec-WebSocket-Protocol"] = protocols.join(",");
      }
      if (opts.origin) {
        if (opts.protocolVersion < 13) {
          opts.headers["Sec-WebSocket-Origin"] = opts.origin;
        } else {
          opts.headers.Origin = opts.origin;
        }
      }
      if (parsedUrl.username || parsedUrl.password) {
        opts.auth = `${parsedUrl.username}:${parsedUrl.password}`;
      }
      if (isIpcUrl) {
        const parts = opts.path.split(":");
        opts.socketPath = parts[0];
        opts.path = parts[1];
      }
      let req;
      if (opts.followRedirects) {
        if (websocket._redirects === 0) {
          websocket._originalIpc = isIpcUrl;
          websocket._originalSecure = isSecure;
          websocket._originalHostOrSocketPath = isIpcUrl ? opts.socketPath : parsedUrl.host;
          const headers = options && options.headers;
          options = { ...options, headers: {} };
          if (headers) {
            for (const [key2, value] of Object.entries(headers)) {
              options.headers[key2.toLowerCase()] = value;
            }
          }
        } else if (websocket.listenerCount("redirect") === 0) {
          const isSameHost = isIpcUrl ? websocket._originalIpc ? opts.socketPath === websocket._originalHostOrSocketPath : false : websocket._originalIpc ? false : parsedUrl.host === websocket._originalHostOrSocketPath;
          if (!isSameHost || websocket._originalSecure && !isSecure) {
            delete opts.headers.authorization;
            delete opts.headers.cookie;
            if (!isSameHost) delete opts.headers.host;
            opts.auth = void 0;
          }
        }
        if (opts.auth && !options.headers.authorization) {
          options.headers.authorization = "Basic " + Buffer.from(opts.auth).toString("base64");
        }
        req = websocket._req = request(opts);
        if (websocket._redirects) {
          websocket.emit("redirect", websocket.url, req);
        }
      } else {
        req = websocket._req = request(opts);
      }
      if (opts.timeout) {
        req.on("timeout", () => {
          abortHandshake(websocket, req, "Opening handshake has timed out");
        });
      }
      req.on("error", (err) => {
        if (req === null || req[kAborted]) return;
        req = websocket._req = null;
        emitErrorAndClose(websocket, err);
      });
      req.on("response", (res) => {
        const location = res.headers.location;
        const statusCode = res.statusCode;
        if (location && opts.followRedirects && statusCode >= 300 && statusCode < 400) {
          if (++websocket._redirects > opts.maxRedirects) {
            abortHandshake(websocket, req, "Maximum redirects exceeded");
            return;
          }
          req.abort();
          let addr;
          try {
            addr = new URL3(location, address);
          } catch (e) {
            const err = new SyntaxError(`Invalid URL: ${location}`);
            emitErrorAndClose(websocket, err);
            return;
          }
          initAsClient(websocket, addr, protocols, options);
        } else if (!websocket.emit("unexpected-response", req, res)) {
          abortHandshake(
            websocket,
            req,
            `Unexpected server response: ${res.statusCode}`
          );
        }
      });
      req.on("upgrade", (res, socket, head) => {
        websocket.emit("upgrade", res);
        if (websocket.readyState !== WebSocket2.CONNECTING) return;
        req = websocket._req = null;
        const upgrade = res.headers.upgrade;
        if (upgrade === void 0 || upgrade.toLowerCase() !== "websocket") {
          abortHandshake(websocket, socket, "Invalid Upgrade header");
          return;
        }
        const digest = createHash("sha1").update(key + GUID).digest("base64");
        if (res.headers["sec-websocket-accept"] !== digest) {
          abortHandshake(websocket, socket, "Invalid Sec-WebSocket-Accept header");
          return;
        }
        const serverProt = res.headers["sec-websocket-protocol"];
        let protError;
        if (serverProt !== void 0) {
          if (!protocolSet.size) {
            protError = "Server sent a subprotocol but none was requested";
          } else if (!protocolSet.has(serverProt)) {
            protError = "Server sent an invalid subprotocol";
          }
        } else if (protocolSet.size) {
          protError = "Server sent no subprotocol";
        }
        if (protError) {
          abortHandshake(websocket, socket, protError);
          return;
        }
        if (serverProt) websocket._protocol = serverProt;
        const secWebSocketExtensions = res.headers["sec-websocket-extensions"];
        if (secWebSocketExtensions !== void 0) {
          if (!perMessageDeflate) {
            const message = "Server sent a Sec-WebSocket-Extensions header but no extension was requested";
            abortHandshake(websocket, socket, message);
            return;
          }
          let extensions;
          try {
            extensions = parse(secWebSocketExtensions);
          } catch (err) {
            const message = "Invalid Sec-WebSocket-Extensions header";
            abortHandshake(websocket, socket, message);
            return;
          }
          const extensionNames = Object.keys(extensions);
          if (extensionNames.length !== 1 || extensionNames[0] !== PerMessageDeflate.extensionName) {
            const message = "Server indicated an extension that was not requested";
            abortHandshake(websocket, socket, message);
            return;
          }
          try {
            perMessageDeflate.accept(extensions[PerMessageDeflate.extensionName]);
          } catch (err) {
            const message = "Invalid Sec-WebSocket-Extensions header";
            abortHandshake(websocket, socket, message);
            return;
          }
          websocket._extensions[PerMessageDeflate.extensionName] = perMessageDeflate;
        }
        websocket.setSocket(socket, head, {
          allowSynchronousEvents: opts.allowSynchronousEvents,
          generateMask: opts.generateMask,
          maxPayload: opts.maxPayload,
          skipUTF8Validation: opts.skipUTF8Validation
        });
      });
      if (opts.finishRequest) {
        opts.finishRequest(req, websocket);
      } else {
        req.end();
      }
    }
    function emitErrorAndClose(websocket, err) {
      websocket._readyState = WebSocket2.CLOSING;
      websocket._errorEmitted = true;
      websocket.emit("error", err);
      websocket.emitClose();
    }
    function netConnect(options) {
      options.path = options.socketPath;
      return net2.connect(options);
    }
    function tlsConnect(options) {
      options.path = void 0;
      if (!options.servername && options.servername !== "") {
        options.servername = net2.isIP(options.host) ? "" : options.host;
      }
      return tls.connect(options);
    }
    function abortHandshake(websocket, stream2, message) {
      websocket._readyState = WebSocket2.CLOSING;
      const err = new Error(message);
      Error.captureStackTrace(err, abortHandshake);
      if (stream2.setHeader) {
        stream2[kAborted] = true;
        stream2.abort();
        if (stream2.socket && !stream2.socket.destroyed) {
          stream2.socket.destroy();
        }
        process.nextTick(emitErrorAndClose, websocket, err);
      } else {
        stream2.destroy(err);
        stream2.once("error", websocket.emit.bind(websocket, "error"));
        stream2.once("close", websocket.emitClose.bind(websocket));
      }
    }
    function sendAfterClose(websocket, data, cb) {
      if (data) {
        const length = isBlob(data) ? data.size : toBuffer(data).length;
        if (websocket._socket) websocket._sender._bufferedBytes += length;
        else websocket._bufferedAmount += length;
      }
      if (cb) {
        const err = new Error(
          `WebSocket is not open: readyState ${websocket.readyState} (${readyStates[websocket.readyState]})`
        );
        process.nextTick(cb, err);
      }
    }
    function receiverOnConclude(code, reason) {
      const websocket = this[kWebSocket];
      websocket._closeFrameReceived = true;
      websocket._closeMessage = reason;
      websocket._closeCode = code;
      if (websocket._socket[kWebSocket] === void 0) return;
      websocket._socket.removeListener("data", socketOnData);
      process.nextTick(resume, websocket._socket);
      if (code === 1005) websocket.close();
      else websocket.close(code, reason);
    }
    function receiverOnDrain() {
      const websocket = this[kWebSocket];
      if (!websocket.isPaused) websocket._socket.resume();
    }
    function receiverOnError(err) {
      const websocket = this[kWebSocket];
      if (websocket._socket[kWebSocket] !== void 0) {
        websocket._socket.removeListener("data", socketOnData);
        process.nextTick(resume, websocket._socket);
        websocket.close(err[kStatusCode]);
      }
      if (!websocket._errorEmitted) {
        websocket._errorEmitted = true;
        websocket.emit("error", err);
      }
    }
    function receiverOnFinish() {
      this[kWebSocket].emitClose();
    }
    function receiverOnMessage(data, isBinary) {
      this[kWebSocket].emit("message", data, isBinary);
    }
    function receiverOnPing(data) {
      const websocket = this[kWebSocket];
      if (websocket._autoPong) websocket.pong(data, !this._isServer, NOOP);
      websocket.emit("ping", data);
    }
    function receiverOnPong(data) {
      this[kWebSocket].emit("pong", data);
    }
    function resume(stream2) {
      stream2.resume();
    }
    function senderOnError(err) {
      const websocket = this[kWebSocket];
      if (websocket.readyState === WebSocket2.CLOSED) return;
      if (websocket.readyState === WebSocket2.OPEN) {
        websocket._readyState = WebSocket2.CLOSING;
        setCloseTimer(websocket);
      }
      this._socket.end();
      if (!websocket._errorEmitted) {
        websocket._errorEmitted = true;
        websocket.emit("error", err);
      }
    }
    function setCloseTimer(websocket) {
      websocket._closeTimer = setTimeout(
        websocket._socket.destroy.bind(websocket._socket),
        websocket._closeTimeout
      );
    }
    function socketOnClose() {
      const websocket = this[kWebSocket];
      this.removeListener("close", socketOnClose);
      this.removeListener("data", socketOnData);
      this.removeListener("end", socketOnEnd);
      websocket._readyState = WebSocket2.CLOSING;
      if (!this._readableState.endEmitted && !websocket._closeFrameReceived && !websocket._receiver._writableState.errorEmitted && this._readableState.length !== 0) {
        const chunk = this.read(this._readableState.length);
        websocket._receiver.write(chunk);
      }
      websocket._receiver.end();
      this[kWebSocket] = void 0;
      clearTimeout(websocket._closeTimer);
      if (websocket._receiver._writableState.finished || websocket._receiver._writableState.errorEmitted) {
        websocket.emitClose();
      } else {
        websocket._receiver.on("error", receiverOnFinish);
        websocket._receiver.on("finish", receiverOnFinish);
      }
    }
    function socketOnData(chunk) {
      if (!this[kWebSocket]._receiver.write(chunk)) {
        this.pause();
      }
    }
    function socketOnEnd() {
      const websocket = this[kWebSocket];
      websocket._readyState = WebSocket2.CLOSING;
      websocket._receiver.end();
      this.end();
    }
    function socketOnError() {
      const websocket = this[kWebSocket];
      this.removeListener("error", socketOnError);
      this.on("error", NOOP);
      if (websocket) {
        websocket._readyState = WebSocket2.CLOSING;
        this.destroy();
      }
    }
  }
});

// ../../node_modules/.pnpm/ws@8.19.0/node_modules/ws/lib/stream.js
var require_stream = __commonJS({
  "../../node_modules/.pnpm/ws@8.19.0/node_modules/ws/lib/stream.js"(exports2, module2) {
    "use strict";
    var WebSocket2 = require_websocket();
    var { Duplex } = require("stream");
    function emitClose(stream2) {
      stream2.emit("close");
    }
    function duplexOnEnd() {
      if (!this.destroyed && this._writableState.finished) {
        this.destroy();
      }
    }
    function duplexOnError(err) {
      this.removeListener("error", duplexOnError);
      this.destroy();
      if (this.listenerCount("error") === 0) {
        this.emit("error", err);
      }
    }
    function createWebSocketStream2(ws, options) {
      let terminateOnDestroy = true;
      const duplex = new Duplex({
        ...options,
        autoDestroy: false,
        emitClose: false,
        objectMode: false,
        writableObjectMode: false
      });
      ws.on("message", function message(msg, isBinary) {
        const data = !isBinary && duplex._readableState.objectMode ? msg.toString() : msg;
        if (!duplex.push(data)) ws.pause();
      });
      ws.once("error", function error(err) {
        if (duplex.destroyed) return;
        terminateOnDestroy = false;
        duplex.destroy(err);
      });
      ws.once("close", function close() {
        if (duplex.destroyed) return;
        duplex.push(null);
      });
      duplex._destroy = function(err, callback) {
        if (ws.readyState === ws.CLOSED) {
          callback(err);
          process.nextTick(emitClose, duplex);
          return;
        }
        let called = false;
        ws.once("error", function error(err2) {
          called = true;
          callback(err2);
        });
        ws.once("close", function close() {
          if (!called) callback(err);
          process.nextTick(emitClose, duplex);
        });
        if (terminateOnDestroy) ws.terminate();
      };
      duplex._final = function(callback) {
        if (ws.readyState === ws.CONNECTING) {
          ws.once("open", function open2() {
            duplex._final(callback);
          });
          return;
        }
        if (ws._socket === null) return;
        if (ws._socket._writableState.finished) {
          callback();
          if (duplex._readableState.endEmitted) duplex.destroy();
        } else {
          ws._socket.once("finish", function finish() {
            callback();
          });
          ws.close();
        }
      };
      duplex._read = function() {
        if (ws.isPaused) ws.resume();
      };
      duplex._write = function(chunk, encoding, callback) {
        if (ws.readyState === ws.CONNECTING) {
          ws.once("open", function open2() {
            duplex._write(chunk, encoding, callback);
          });
          return;
        }
        ws.send(chunk, callback);
      };
      duplex.on("end", duplexOnEnd);
      duplex.on("error", duplexOnError);
      return duplex;
    }
    module2.exports = createWebSocketStream2;
  }
});

// ../../node_modules/.pnpm/ws@8.19.0/node_modules/ws/lib/subprotocol.js
var require_subprotocol = __commonJS({
  "../../node_modules/.pnpm/ws@8.19.0/node_modules/ws/lib/subprotocol.js"(exports2, module2) {
    "use strict";
    var { tokenChars } = require_validation();
    function parse(header) {
      const protocols = /* @__PURE__ */ new Set();
      let start = -1;
      let end = -1;
      let i = 0;
      for (i; i < header.length; i++) {
        const code = header.charCodeAt(i);
        if (end === -1 && tokenChars[code] === 1) {
          if (start === -1) start = i;
        } else if (i !== 0 && (code === 32 || code === 9)) {
          if (end === -1 && start !== -1) end = i;
        } else if (code === 44) {
          if (start === -1) {
            throw new SyntaxError(`Unexpected character at index ${i}`);
          }
          if (end === -1) end = i;
          const protocol2 = header.slice(start, end);
          if (protocols.has(protocol2)) {
            throw new SyntaxError(`The "${protocol2}" subprotocol is duplicated`);
          }
          protocols.add(protocol2);
          start = end = -1;
        } else {
          throw new SyntaxError(`Unexpected character at index ${i}`);
        }
      }
      if (start === -1 || end !== -1) {
        throw new SyntaxError("Unexpected end of input");
      }
      const protocol = header.slice(start, i);
      if (protocols.has(protocol)) {
        throw new SyntaxError(`The "${protocol}" subprotocol is duplicated`);
      }
      protocols.add(protocol);
      return protocols;
    }
    module2.exports = { parse };
  }
});

// ../../node_modules/.pnpm/ws@8.19.0/node_modules/ws/lib/websocket-server.js
var require_websocket_server = __commonJS({
  "../../node_modules/.pnpm/ws@8.19.0/node_modules/ws/lib/websocket-server.js"(exports2, module2) {
    "use strict";
    var EventEmitter = require("events");
    var http2 = require("http");
    var { Duplex } = require("stream");
    var { createHash } = require("crypto");
    var extension = require_extension();
    var PerMessageDeflate = require_permessage_deflate();
    var subprotocol = require_subprotocol();
    var WebSocket2 = require_websocket();
    var { CLOSE_TIMEOUT, GUID, kWebSocket } = require_constants();
    var keyRegex = /^[+/0-9A-Za-z]{22}==$/;
    var RUNNING = 0;
    var CLOSING = 1;
    var CLOSED = 2;
    var WebSocketServer2 = class extends EventEmitter {
      /**
       * Create a `WebSocketServer` instance.
       *
       * @param {Object} options Configuration options
       * @param {Boolean} [options.allowSynchronousEvents=true] Specifies whether
       *     any of the `'message'`, `'ping'`, and `'pong'` events can be emitted
       *     multiple times in the same tick
       * @param {Boolean} [options.autoPong=true] Specifies whether or not to
       *     automatically send a pong in response to a ping
       * @param {Number} [options.backlog=511] The maximum length of the queue of
       *     pending connections
       * @param {Boolean} [options.clientTracking=true] Specifies whether or not to
       *     track clients
       * @param {Number} [options.closeTimeout=30000] Duration in milliseconds to
       *     wait for the closing handshake to finish after `websocket.close()` is
       *     called
       * @param {Function} [options.handleProtocols] A hook to handle protocols
       * @param {String} [options.host] The hostname where to bind the server
       * @param {Number} [options.maxPayload=104857600] The maximum allowed message
       *     size
       * @param {Boolean} [options.noServer=false] Enable no server mode
       * @param {String} [options.path] Accept only connections matching this path
       * @param {(Boolean|Object)} [options.perMessageDeflate=false] Enable/disable
       *     permessage-deflate
       * @param {Number} [options.port] The port where to bind the server
       * @param {(http.Server|https.Server)} [options.server] A pre-created HTTP/S
       *     server to use
       * @param {Boolean} [options.skipUTF8Validation=false] Specifies whether or
       *     not to skip UTF-8 validation for text and close messages
       * @param {Function} [options.verifyClient] A hook to reject connections
       * @param {Function} [options.WebSocket=WebSocket] Specifies the `WebSocket`
       *     class to use. It must be the `WebSocket` class or class that extends it
       * @param {Function} [callback] A listener for the `listening` event
       */
      constructor(options, callback) {
        super();
        options = {
          allowSynchronousEvents: true,
          autoPong: true,
          maxPayload: 100 * 1024 * 1024,
          skipUTF8Validation: false,
          perMessageDeflate: false,
          handleProtocols: null,
          clientTracking: true,
          closeTimeout: CLOSE_TIMEOUT,
          verifyClient: null,
          noServer: false,
          backlog: null,
          // use default (511 as implemented in net.js)
          server: null,
          host: null,
          path: null,
          port: null,
          WebSocket: WebSocket2,
          ...options
        };
        if (options.port == null && !options.server && !options.noServer || options.port != null && (options.server || options.noServer) || options.server && options.noServer) {
          throw new TypeError(
            'One and only one of the "port", "server", or "noServer" options must be specified'
          );
        }
        if (options.port != null) {
          this._server = http2.createServer((req, res) => {
            const body = http2.STATUS_CODES[426];
            res.writeHead(426, {
              "Content-Length": body.length,
              "Content-Type": "text/plain"
            });
            res.end(body);
          });
          this._server.listen(
            options.port,
            options.host,
            options.backlog,
            callback
          );
        } else if (options.server) {
          this._server = options.server;
        }
        if (this._server) {
          const emitConnection = this.emit.bind(this, "connection");
          this._removeListeners = addListeners(this._server, {
            listening: this.emit.bind(this, "listening"),
            error: this.emit.bind(this, "error"),
            upgrade: (req, socket, head) => {
              this.handleUpgrade(req, socket, head, emitConnection);
            }
          });
        }
        if (options.perMessageDeflate === true) options.perMessageDeflate = {};
        if (options.clientTracking) {
          this.clients = /* @__PURE__ */ new Set();
          this._shouldEmitClose = false;
        }
        this.options = options;
        this._state = RUNNING;
      }
      /**
       * Returns the bound address, the address family name, and port of the server
       * as reported by the operating system if listening on an IP socket.
       * If the server is listening on a pipe or UNIX domain socket, the name is
       * returned as a string.
       *
       * @return {(Object|String|null)} The address of the server
       * @public
       */
      address() {
        if (this.options.noServer) {
          throw new Error('The server is operating in "noServer" mode');
        }
        if (!this._server) return null;
        return this._server.address();
      }
      /**
       * Stop the server from accepting new connections and emit the `'close'` event
       * when all existing connections are closed.
       *
       * @param {Function} [cb] A one-time listener for the `'close'` event
       * @public
       */
      close(cb) {
        if (this._state === CLOSED) {
          if (cb) {
            this.once("close", () => {
              cb(new Error("The server is not running"));
            });
          }
          process.nextTick(emitClose, this);
          return;
        }
        if (cb) this.once("close", cb);
        if (this._state === CLOSING) return;
        this._state = CLOSING;
        if (this.options.noServer || this.options.server) {
          if (this._server) {
            this._removeListeners();
            this._removeListeners = this._server = null;
          }
          if (this.clients) {
            if (!this.clients.size) {
              process.nextTick(emitClose, this);
            } else {
              this._shouldEmitClose = true;
            }
          } else {
            process.nextTick(emitClose, this);
          }
        } else {
          const server = this._server;
          this._removeListeners();
          this._removeListeners = this._server = null;
          server.close(() => {
            emitClose(this);
          });
        }
      }
      /**
       * See if a given request should be handled by this server instance.
       *
       * @param {http.IncomingMessage} req Request object to inspect
       * @return {Boolean} `true` if the request is valid, else `false`
       * @public
       */
      shouldHandle(req) {
        if (this.options.path) {
          const index = req.url.indexOf("?");
          const pathname = index !== -1 ? req.url.slice(0, index) : req.url;
          if (pathname !== this.options.path) return false;
        }
        return true;
      }
      /**
       * Handle a HTTP Upgrade request.
       *
       * @param {http.IncomingMessage} req The request object
       * @param {Duplex} socket The network socket between the server and client
       * @param {Buffer} head The first packet of the upgraded stream
       * @param {Function} cb Callback
       * @public
       */
      handleUpgrade(req, socket, head, cb) {
        socket.on("error", socketOnError);
        const key = req.headers["sec-websocket-key"];
        const upgrade = req.headers.upgrade;
        const version = +req.headers["sec-websocket-version"];
        if (req.method !== "GET") {
          const message = "Invalid HTTP method";
          abortHandshakeOrEmitwsClientError(this, req, socket, 405, message);
          return;
        }
        if (upgrade === void 0 || upgrade.toLowerCase() !== "websocket") {
          const message = "Invalid Upgrade header";
          abortHandshakeOrEmitwsClientError(this, req, socket, 400, message);
          return;
        }
        if (key === void 0 || !keyRegex.test(key)) {
          const message = "Missing or invalid Sec-WebSocket-Key header";
          abortHandshakeOrEmitwsClientError(this, req, socket, 400, message);
          return;
        }
        if (version !== 13 && version !== 8) {
          const message = "Missing or invalid Sec-WebSocket-Version header";
          abortHandshakeOrEmitwsClientError(this, req, socket, 400, message, {
            "Sec-WebSocket-Version": "13, 8"
          });
          return;
        }
        if (!this.shouldHandle(req)) {
          abortHandshake(socket, 400);
          return;
        }
        const secWebSocketProtocol = req.headers["sec-websocket-protocol"];
        let protocols = /* @__PURE__ */ new Set();
        if (secWebSocketProtocol !== void 0) {
          try {
            protocols = subprotocol.parse(secWebSocketProtocol);
          } catch (err) {
            const message = "Invalid Sec-WebSocket-Protocol header";
            abortHandshakeOrEmitwsClientError(this, req, socket, 400, message);
            return;
          }
        }
        const secWebSocketExtensions = req.headers["sec-websocket-extensions"];
        const extensions = {};
        if (this.options.perMessageDeflate && secWebSocketExtensions !== void 0) {
          const perMessageDeflate = new PerMessageDeflate(
            this.options.perMessageDeflate,
            true,
            this.options.maxPayload
          );
          try {
            const offers = extension.parse(secWebSocketExtensions);
            if (offers[PerMessageDeflate.extensionName]) {
              perMessageDeflate.accept(offers[PerMessageDeflate.extensionName]);
              extensions[PerMessageDeflate.extensionName] = perMessageDeflate;
            }
          } catch (err) {
            const message = "Invalid or unacceptable Sec-WebSocket-Extensions header";
            abortHandshakeOrEmitwsClientError(this, req, socket, 400, message);
            return;
          }
        }
        if (this.options.verifyClient) {
          const info = {
            origin: req.headers[`${version === 8 ? "sec-websocket-origin" : "origin"}`],
            secure: !!(req.socket.authorized || req.socket.encrypted),
            req
          };
          if (this.options.verifyClient.length === 2) {
            this.options.verifyClient(info, (verified, code, message, headers) => {
              if (!verified) {
                return abortHandshake(socket, code || 401, message, headers);
              }
              this.completeUpgrade(
                extensions,
                key,
                protocols,
                req,
                socket,
                head,
                cb
              );
            });
            return;
          }
          if (!this.options.verifyClient(info)) return abortHandshake(socket, 401);
        }
        this.completeUpgrade(extensions, key, protocols, req, socket, head, cb);
      }
      /**
       * Upgrade the connection to WebSocket.
       *
       * @param {Object} extensions The accepted extensions
       * @param {String} key The value of the `Sec-WebSocket-Key` header
       * @param {Set} protocols The subprotocols
       * @param {http.IncomingMessage} req The request object
       * @param {Duplex} socket The network socket between the server and client
       * @param {Buffer} head The first packet of the upgraded stream
       * @param {Function} cb Callback
       * @throws {Error} If called more than once with the same socket
       * @private
       */
      completeUpgrade(extensions, key, protocols, req, socket, head, cb) {
        if (!socket.readable || !socket.writable) return socket.destroy();
        if (socket[kWebSocket]) {
          throw new Error(
            "server.handleUpgrade() was called more than once with the same socket, possibly due to a misconfiguration"
          );
        }
        if (this._state > RUNNING) return abortHandshake(socket, 503);
        const digest = createHash("sha1").update(key + GUID).digest("base64");
        const headers = [
          "HTTP/1.1 101 Switching Protocols",
          "Upgrade: websocket",
          "Connection: Upgrade",
          `Sec-WebSocket-Accept: ${digest}`
        ];
        const ws = new this.options.WebSocket(null, void 0, this.options);
        if (protocols.size) {
          const protocol = this.options.handleProtocols ? this.options.handleProtocols(protocols, req) : protocols.values().next().value;
          if (protocol) {
            headers.push(`Sec-WebSocket-Protocol: ${protocol}`);
            ws._protocol = protocol;
          }
        }
        if (extensions[PerMessageDeflate.extensionName]) {
          const params = extensions[PerMessageDeflate.extensionName].params;
          const value = extension.format({
            [PerMessageDeflate.extensionName]: [params]
          });
          headers.push(`Sec-WebSocket-Extensions: ${value}`);
          ws._extensions = extensions;
        }
        this.emit("headers", headers, req);
        socket.write(headers.concat("\r\n").join("\r\n"));
        socket.removeListener("error", socketOnError);
        ws.setSocket(socket, head, {
          allowSynchronousEvents: this.options.allowSynchronousEvents,
          maxPayload: this.options.maxPayload,
          skipUTF8Validation: this.options.skipUTF8Validation
        });
        if (this.clients) {
          this.clients.add(ws);
          ws.on("close", () => {
            this.clients.delete(ws);
            if (this._shouldEmitClose && !this.clients.size) {
              process.nextTick(emitClose, this);
            }
          });
        }
        cb(ws, req);
      }
    };
    module2.exports = WebSocketServer2;
    function addListeners(server, map) {
      for (const event of Object.keys(map)) server.on(event, map[event]);
      return function removeListeners() {
        for (const event of Object.keys(map)) {
          server.removeListener(event, map[event]);
        }
      };
    }
    function emitClose(server) {
      server._state = CLOSED;
      server.emit("close");
    }
    function socketOnError() {
      this.destroy();
    }
    function abortHandshake(socket, code, message, headers) {
      message = message || http2.STATUS_CODES[code];
      headers = {
        Connection: "close",
        "Content-Type": "text/html",
        "Content-Length": Buffer.byteLength(message),
        ...headers
      };
      socket.once("finish", socket.destroy);
      socket.end(
        `HTTP/1.1 ${code} ${http2.STATUS_CODES[code]}\r
` + Object.keys(headers).map((h) => `${h}: ${headers[h]}`).join("\r\n") + "\r\n\r\n" + message
      );
    }
    function abortHandshakeOrEmitwsClientError(server, req, socket, code, message, headers) {
      if (server.listenerCount("wsClientError")) {
        const err = new Error(message);
        Error.captureStackTrace(err, abortHandshakeOrEmitwsClientError);
        server.emit("wsClientError", err, socket, req);
      } else {
        abortHandshake(socket, code, message, headers);
      }
    }
  }
});

// ../../node_modules/.pnpm/@hono+node-server@1.19.11_hono@4.12.5/node_modules/@hono/node-server/dist/index.mjs
var import_http = require("http");
var import_http2 = require("http2");
var import_http22 = require("http2");
var import_stream = require("stream");
var import_crypto = __toESM(require("crypto"), 1);
var RequestError = class extends Error {
  constructor(message, options) {
    super(message, options);
    this.name = "RequestError";
  }
};
var toRequestError = (e) => {
  if (e instanceof RequestError) {
    return e;
  }
  return new RequestError(e.message, { cause: e });
};
var GlobalRequest = global.Request;
var Request2 = class extends GlobalRequest {
  constructor(input, options) {
    if (typeof input === "object" && getRequestCache in input) {
      input = input[getRequestCache]();
    }
    if (typeof options?.body?.getReader !== "undefined") {
      ;
      options.duplex ??= "half";
    }
    super(input, options);
  }
};
var newHeadersFromIncoming = (incoming) => {
  const headerRecord = [];
  const rawHeaders = incoming.rawHeaders;
  for (let i = 0; i < rawHeaders.length; i += 2) {
    const { [i]: key, [i + 1]: value } = rawHeaders;
    if (key.charCodeAt(0) !== /*:*/
    58) {
      headerRecord.push([key, value]);
    }
  }
  return new Headers(headerRecord);
};
var wrapBodyStream = Symbol("wrapBodyStream");
var newRequestFromIncoming = (method, url, headers, incoming, abortController) => {
  const init = {
    method,
    headers,
    signal: abortController.signal
  };
  if (method === "TRACE") {
    init.method = "GET";
    const req = new Request2(url, init);
    Object.defineProperty(req, "method", {
      get() {
        return "TRACE";
      }
    });
    return req;
  }
  if (!(method === "GET" || method === "HEAD")) {
    if ("rawBody" in incoming && incoming.rawBody instanceof Buffer) {
      init.body = new ReadableStream({
        start(controller) {
          controller.enqueue(incoming.rawBody);
          controller.close();
        }
      });
    } else if (incoming[wrapBodyStream]) {
      let reader;
      init.body = new ReadableStream({
        async pull(controller) {
          try {
            reader ||= import_stream.Readable.toWeb(incoming).getReader();
            const { done, value } = await reader.read();
            if (done) {
              controller.close();
            } else {
              controller.enqueue(value);
            }
          } catch (error) {
            controller.error(error);
          }
        }
      });
    } else {
      init.body = import_stream.Readable.toWeb(incoming);
    }
  }
  return new Request2(url, init);
};
var getRequestCache = Symbol("getRequestCache");
var requestCache = Symbol("requestCache");
var incomingKey = Symbol("incomingKey");
var urlKey = Symbol("urlKey");
var headersKey = Symbol("headersKey");
var abortControllerKey = Symbol("abortControllerKey");
var getAbortController = Symbol("getAbortController");
var requestPrototype = {
  get method() {
    return this[incomingKey].method || "GET";
  },
  get url() {
    return this[urlKey];
  },
  get headers() {
    return this[headersKey] ||= newHeadersFromIncoming(this[incomingKey]);
  },
  [getAbortController]() {
    this[getRequestCache]();
    return this[abortControllerKey];
  },
  [getRequestCache]() {
    this[abortControllerKey] ||= new AbortController();
    return this[requestCache] ||= newRequestFromIncoming(
      this.method,
      this[urlKey],
      this.headers,
      this[incomingKey],
      this[abortControllerKey]
    );
  }
};
[
  "body",
  "bodyUsed",
  "cache",
  "credentials",
  "destination",
  "integrity",
  "mode",
  "redirect",
  "referrer",
  "referrerPolicy",
  "signal",
  "keepalive"
].forEach((k) => {
  Object.defineProperty(requestPrototype, k, {
    get() {
      return this[getRequestCache]()[k];
    }
  });
});
["arrayBuffer", "blob", "clone", "formData", "json", "text"].forEach((k) => {
  Object.defineProperty(requestPrototype, k, {
    value: function() {
      return this[getRequestCache]()[k]();
    }
  });
});
Object.setPrototypeOf(requestPrototype, Request2.prototype);
var newRequest = (incoming, defaultHostname) => {
  const req = Object.create(requestPrototype);
  req[incomingKey] = incoming;
  const incomingUrl = incoming.url || "";
  if (incomingUrl[0] !== "/" && // short-circuit for performance. most requests are relative URL.
  (incomingUrl.startsWith("http://") || incomingUrl.startsWith("https://"))) {
    if (incoming instanceof import_http22.Http2ServerRequest) {
      throw new RequestError("Absolute URL for :path is not allowed in HTTP/2");
    }
    try {
      const url2 = new URL(incomingUrl);
      req[urlKey] = url2.href;
    } catch (e) {
      throw new RequestError("Invalid absolute URL", { cause: e });
    }
    return req;
  }
  const host = (incoming instanceof import_http22.Http2ServerRequest ? incoming.authority : incoming.headers.host) || defaultHostname;
  if (!host) {
    throw new RequestError("Missing host header");
  }
  let scheme;
  if (incoming instanceof import_http22.Http2ServerRequest) {
    scheme = incoming.scheme;
    if (!(scheme === "http" || scheme === "https")) {
      throw new RequestError("Unsupported scheme");
    }
  } else {
    scheme = incoming.socket && incoming.socket.encrypted ? "https" : "http";
  }
  const url = new URL(`${scheme}://${host}${incomingUrl}`);
  if (url.hostname.length !== host.length && url.hostname !== host.replace(/:\d+$/, "")) {
    throw new RequestError("Invalid host header");
  }
  req[urlKey] = url.href;
  return req;
};
var responseCache = Symbol("responseCache");
var getResponseCache = Symbol("getResponseCache");
var cacheKey = Symbol("cache");
var GlobalResponse = global.Response;
var Response2 = class _Response {
  #body;
  #init;
  [getResponseCache]() {
    delete this[cacheKey];
    return this[responseCache] ||= new GlobalResponse(this.#body, this.#init);
  }
  constructor(body, init) {
    let headers;
    this.#body = body;
    if (init instanceof _Response) {
      const cachedGlobalResponse = init[responseCache];
      if (cachedGlobalResponse) {
        this.#init = cachedGlobalResponse;
        this[getResponseCache]();
        return;
      } else {
        this.#init = init.#init;
        headers = new Headers(init.#init.headers);
      }
    } else {
      this.#init = init;
    }
    if (typeof body === "string" || typeof body?.getReader !== "undefined" || body instanceof Blob || body instanceof Uint8Array) {
      ;
      this[cacheKey] = [init?.status || 200, body, headers || init?.headers];
    }
  }
  get headers() {
    const cache = this[cacheKey];
    if (cache) {
      if (!(cache[2] instanceof Headers)) {
        cache[2] = new Headers(
          cache[2] || { "content-type": "text/plain; charset=UTF-8" }
        );
      }
      return cache[2];
    }
    return this[getResponseCache]().headers;
  }
  get status() {
    return this[cacheKey]?.[0] ?? this[getResponseCache]().status;
  }
  get ok() {
    const status = this.status;
    return status >= 200 && status < 300;
  }
};
["body", "bodyUsed", "redirected", "statusText", "trailers", "type", "url"].forEach((k) => {
  Object.defineProperty(Response2.prototype, k, {
    get() {
      return this[getResponseCache]()[k];
    }
  });
});
["arrayBuffer", "blob", "clone", "formData", "json", "text"].forEach((k) => {
  Object.defineProperty(Response2.prototype, k, {
    value: function() {
      return this[getResponseCache]()[k]();
    }
  });
});
Object.setPrototypeOf(Response2, GlobalResponse);
Object.setPrototypeOf(Response2.prototype, GlobalResponse.prototype);
async function readWithoutBlocking(readPromise) {
  return Promise.race([readPromise, Promise.resolve().then(() => Promise.resolve(void 0))]);
}
function writeFromReadableStreamDefaultReader(reader, writable, currentReadPromise) {
  const cancel = (error) => {
    reader.cancel(error).catch(() => {
    });
  };
  writable.on("close", cancel);
  writable.on("error", cancel);
  (currentReadPromise ?? reader.read()).then(flow, handleStreamError);
  return reader.closed.finally(() => {
    writable.off("close", cancel);
    writable.off("error", cancel);
  });
  function handleStreamError(error) {
    if (error) {
      writable.destroy(error);
    }
  }
  function onDrain() {
    reader.read().then(flow, handleStreamError);
  }
  function flow({ done, value }) {
    try {
      if (done) {
        writable.end();
      } else if (!writable.write(value)) {
        writable.once("drain", onDrain);
      } else {
        return reader.read().then(flow, handleStreamError);
      }
    } catch (e) {
      handleStreamError(e);
    }
  }
}
function writeFromReadableStream(stream2, writable) {
  if (stream2.locked) {
    throw new TypeError("ReadableStream is locked.");
  } else if (writable.destroyed) {
    return;
  }
  return writeFromReadableStreamDefaultReader(stream2.getReader(), writable);
}
var buildOutgoingHttpHeaders = (headers) => {
  const res = {};
  if (!(headers instanceof Headers)) {
    headers = new Headers(headers ?? void 0);
  }
  const cookies = [];
  for (const [k, v] of headers) {
    if (k === "set-cookie") {
      cookies.push(v);
    } else {
      res[k] = v;
    }
  }
  if (cookies.length > 0) {
    res["set-cookie"] = cookies;
  }
  res["content-type"] ??= "text/plain; charset=UTF-8";
  return res;
};
var X_ALREADY_SENT = "x-hono-already-sent";
if (typeof global.crypto === "undefined") {
  global.crypto = import_crypto.default;
}
var outgoingEnded = Symbol("outgoingEnded");
var handleRequestError = () => new Response(null, {
  status: 400
});
var handleFetchError = (e) => new Response(null, {
  status: e instanceof Error && (e.name === "TimeoutError" || e.constructor.name === "TimeoutError") ? 504 : 500
});
var handleResponseError = (e, outgoing) => {
  const err = e instanceof Error ? e : new Error("unknown error", { cause: e });
  if (err.code === "ERR_STREAM_PREMATURE_CLOSE") {
    console.info("The user aborted a request.");
  } else {
    console.error(e);
    if (!outgoing.headersSent) {
      outgoing.writeHead(500, { "Content-Type": "text/plain" });
    }
    outgoing.end(`Error: ${err.message}`);
    outgoing.destroy(err);
  }
};
var flushHeaders = (outgoing) => {
  if ("flushHeaders" in outgoing && outgoing.writable) {
    outgoing.flushHeaders();
  }
};
var responseViaCache = async (res, outgoing) => {
  let [status, body, header] = res[cacheKey];
  let hasContentLength = false;
  if (!header) {
    header = { "content-type": "text/plain; charset=UTF-8" };
  } else if (header instanceof Headers) {
    hasContentLength = header.has("content-length");
    header = buildOutgoingHttpHeaders(header);
  } else if (Array.isArray(header)) {
    const headerObj = new Headers(header);
    hasContentLength = headerObj.has("content-length");
    header = buildOutgoingHttpHeaders(headerObj);
  } else {
    for (const key in header) {
      if (key.length === 14 && key.toLowerCase() === "content-length") {
        hasContentLength = true;
        break;
      }
    }
  }
  if (!hasContentLength) {
    if (typeof body === "string") {
      header["Content-Length"] = Buffer.byteLength(body);
    } else if (body instanceof Uint8Array) {
      header["Content-Length"] = body.byteLength;
    } else if (body instanceof Blob) {
      header["Content-Length"] = body.size;
    }
  }
  outgoing.writeHead(status, header);
  if (typeof body === "string" || body instanceof Uint8Array) {
    outgoing.end(body);
  } else if (body instanceof Blob) {
    outgoing.end(new Uint8Array(await body.arrayBuffer()));
  } else {
    flushHeaders(outgoing);
    await writeFromReadableStream(body, outgoing)?.catch(
      (e) => handleResponseError(e, outgoing)
    );
  }
  ;
  outgoing[outgoingEnded]?.();
};
var isPromise = (res) => typeof res.then === "function";
var responseViaResponseObject = async (res, outgoing, options = {}) => {
  if (isPromise(res)) {
    if (options.errorHandler) {
      try {
        res = await res;
      } catch (err) {
        const errRes = await options.errorHandler(err);
        if (!errRes) {
          return;
        }
        res = errRes;
      }
    } else {
      res = await res.catch(handleFetchError);
    }
  }
  if (cacheKey in res) {
    return responseViaCache(res, outgoing);
  }
  const resHeaderRecord = buildOutgoingHttpHeaders(res.headers);
  if (res.body) {
    const reader = res.body.getReader();
    const values = [];
    let done = false;
    let currentReadPromise = void 0;
    if (resHeaderRecord["transfer-encoding"] !== "chunked") {
      let maxReadCount = 2;
      for (let i = 0; i < maxReadCount; i++) {
        currentReadPromise ||= reader.read();
        const chunk = await readWithoutBlocking(currentReadPromise).catch((e) => {
          console.error(e);
          done = true;
        });
        if (!chunk) {
          if (i === 1) {
            await new Promise((resolve2) => setTimeout(resolve2));
            maxReadCount = 3;
            continue;
          }
          break;
        }
        currentReadPromise = void 0;
        if (chunk.value) {
          values.push(chunk.value);
        }
        if (chunk.done) {
          done = true;
          break;
        }
      }
      if (done && !("content-length" in resHeaderRecord)) {
        resHeaderRecord["content-length"] = values.reduce((acc, value) => acc + value.length, 0);
      }
    }
    outgoing.writeHead(res.status, resHeaderRecord);
    values.forEach((value) => {
      ;
      outgoing.write(value);
    });
    if (done) {
      outgoing.end();
    } else {
      if (values.length === 0) {
        flushHeaders(outgoing);
      }
      await writeFromReadableStreamDefaultReader(reader, outgoing, currentReadPromise);
    }
  } else if (resHeaderRecord[X_ALREADY_SENT]) {
  } else {
    outgoing.writeHead(res.status, resHeaderRecord);
    outgoing.end();
  }
  ;
  outgoing[outgoingEnded]?.();
};
var getRequestListener = (fetchCallback, options = {}) => {
  const autoCleanupIncoming = options.autoCleanupIncoming ?? true;
  if (options.overrideGlobalObjects !== false && global.Request !== Request2) {
    Object.defineProperty(global, "Request", {
      value: Request2
    });
    Object.defineProperty(global, "Response", {
      value: Response2
    });
  }
  return async (incoming, outgoing) => {
    let res, req;
    try {
      req = newRequest(incoming, options.hostname);
      let incomingEnded = !autoCleanupIncoming || incoming.method === "GET" || incoming.method === "HEAD";
      if (!incomingEnded) {
        ;
        incoming[wrapBodyStream] = true;
        incoming.on("end", () => {
          incomingEnded = true;
        });
        if (incoming instanceof import_http2.Http2ServerRequest) {
          ;
          outgoing[outgoingEnded] = () => {
            if (!incomingEnded) {
              setTimeout(() => {
                if (!incomingEnded) {
                  setTimeout(() => {
                    incoming.destroy();
                    outgoing.destroy();
                  });
                }
              });
            }
          };
        }
      }
      outgoing.on("close", () => {
        const abortController = req[abortControllerKey];
        if (abortController) {
          if (incoming.errored) {
            req[abortControllerKey].abort(incoming.errored.toString());
          } else if (!outgoing.writableFinished) {
            req[abortControllerKey].abort("Client connection prematurely closed.");
          }
        }
        if (!incomingEnded) {
          setTimeout(() => {
            if (!incomingEnded) {
              setTimeout(() => {
                incoming.destroy();
              });
            }
          });
        }
      });
      res = fetchCallback(req, { incoming, outgoing });
      if (cacheKey in res) {
        return responseViaCache(res, outgoing);
      }
    } catch (e) {
      if (!res) {
        if (options.errorHandler) {
          res = await options.errorHandler(req ? e : toRequestError(e));
          if (!res) {
            return;
          }
        } else if (!req) {
          res = handleRequestError();
        } else {
          res = handleFetchError(e);
        }
      } else {
        return handleResponseError(e, outgoing);
      }
    }
    try {
      return await responseViaResponseObject(res, outgoing, options);
    } catch (e) {
      return handleResponseError(e, outgoing);
    }
  };
};
var createAdaptorServer = (options) => {
  const fetchCallback = options.fetch;
  const requestListener = getRequestListener(fetchCallback, {
    hostname: options.hostname,
    overrideGlobalObjects: options.overrideGlobalObjects,
    autoCleanupIncoming: options.autoCleanupIncoming
  });
  const createServer = options.createServer || import_http.createServer;
  const server = createServer(options.serverOptions || {}, requestListener);
  return server;
};

// ../../node_modules/.pnpm/hono@4.12.5/node_modules/hono/dist/compose.js
var compose = (middleware, onError, onNotFound) => {
  return (context, next) => {
    let index = -1;
    return dispatch(0);
    async function dispatch(i) {
      if (i <= index) {
        throw new Error("next() called multiple times");
      }
      index = i;
      let res;
      let isError = false;
      let handler;
      if (middleware[i]) {
        handler = middleware[i][0][0];
        context.req.routeIndex = i;
      } else {
        handler = i === middleware.length && next || void 0;
      }
      if (handler) {
        try {
          res = await handler(context, () => dispatch(i + 1));
        } catch (err) {
          if (err instanceof Error && onError) {
            context.error = err;
            res = await onError(err, context);
            isError = true;
          } else {
            throw err;
          }
        }
      } else {
        if (context.finalized === false && onNotFound) {
          res = await onNotFound(context);
        }
      }
      if (res && (context.finalized === false || isError)) {
        context.res = res;
      }
      return context;
    }
  };
};

// ../../node_modules/.pnpm/hono@4.12.5/node_modules/hono/dist/request/constants.js
var GET_MATCH_RESULT = /* @__PURE__ */ Symbol();

// ../../node_modules/.pnpm/hono@4.12.5/node_modules/hono/dist/utils/body.js
var parseBody = async (request, options = /* @__PURE__ */ Object.create(null)) => {
  const { all = false, dot = false } = options;
  const headers = request instanceof HonoRequest ? request.raw.headers : request.headers;
  const contentType = headers.get("Content-Type");
  if (contentType?.startsWith("multipart/form-data") || contentType?.startsWith("application/x-www-form-urlencoded")) {
    return parseFormData(request, { all, dot });
  }
  return {};
};
async function parseFormData(request, options) {
  const formData = await request.formData();
  if (formData) {
    return convertFormDataToBodyData(formData, options);
  }
  return {};
}
function convertFormDataToBodyData(formData, options) {
  const form = /* @__PURE__ */ Object.create(null);
  formData.forEach((value, key) => {
    const shouldParseAllValues = options.all || key.endsWith("[]");
    if (!shouldParseAllValues) {
      form[key] = value;
    } else {
      handleParsingAllValues(form, key, value);
    }
  });
  if (options.dot) {
    Object.entries(form).forEach(([key, value]) => {
      const shouldParseDotValues = key.includes(".");
      if (shouldParseDotValues) {
        handleParsingNestedValues(form, key, value);
        delete form[key];
      }
    });
  }
  return form;
}
var handleParsingAllValues = (form, key, value) => {
  if (form[key] !== void 0) {
    if (Array.isArray(form[key])) {
      ;
      form[key].push(value);
    } else {
      form[key] = [form[key], value];
    }
  } else {
    if (!key.endsWith("[]")) {
      form[key] = value;
    } else {
      form[key] = [value];
    }
  }
};
var handleParsingNestedValues = (form, key, value) => {
  let nestedForm = form;
  const keys = key.split(".");
  keys.forEach((key2, index) => {
    if (index === keys.length - 1) {
      nestedForm[key2] = value;
    } else {
      if (!nestedForm[key2] || typeof nestedForm[key2] !== "object" || Array.isArray(nestedForm[key2]) || nestedForm[key2] instanceof File) {
        nestedForm[key2] = /* @__PURE__ */ Object.create(null);
      }
      nestedForm = nestedForm[key2];
    }
  });
};

// ../../node_modules/.pnpm/hono@4.12.5/node_modules/hono/dist/utils/url.js
var splitPath = (path) => {
  const paths = path.split("/");
  if (paths[0] === "") {
    paths.shift();
  }
  return paths;
};
var splitRoutingPath = (routePath) => {
  const { groups, path } = extractGroupsFromPath(routePath);
  const paths = splitPath(path);
  return replaceGroupMarks(paths, groups);
};
var extractGroupsFromPath = (path) => {
  const groups = [];
  path = path.replace(/\{[^}]+\}/g, (match2, index) => {
    const mark = `@${index}`;
    groups.push([mark, match2]);
    return mark;
  });
  return { groups, path };
};
var replaceGroupMarks = (paths, groups) => {
  for (let i = groups.length - 1; i >= 0; i--) {
    const [mark] = groups[i];
    for (let j = paths.length - 1; j >= 0; j--) {
      if (paths[j].includes(mark)) {
        paths[j] = paths[j].replace(mark, groups[i][1]);
        break;
      }
    }
  }
  return paths;
};
var patternCache = {};
var getPattern = (label, next) => {
  if (label === "*") {
    return "*";
  }
  const match2 = label.match(/^\:([^\{\}]+)(?:\{(.+)\})?$/);
  if (match2) {
    const cacheKey2 = `${label}#${next}`;
    if (!patternCache[cacheKey2]) {
      if (match2[2]) {
        patternCache[cacheKey2] = next && next[0] !== ":" && next[0] !== "*" ? [cacheKey2, match2[1], new RegExp(`^${match2[2]}(?=/${next})`)] : [label, match2[1], new RegExp(`^${match2[2]}$`)];
      } else {
        patternCache[cacheKey2] = [label, match2[1], true];
      }
    }
    return patternCache[cacheKey2];
  }
  return null;
};
var tryDecode = (str, decoder) => {
  try {
    return decoder(str);
  } catch {
    return str.replace(/(?:%[0-9A-Fa-f]{2})+/g, (match2) => {
      try {
        return decoder(match2);
      } catch {
        return match2;
      }
    });
  }
};
var tryDecodeURI = (str) => tryDecode(str, decodeURI);
var getPath = (request) => {
  const url = request.url;
  const start = url.indexOf("/", url.indexOf(":") + 4);
  let i = start;
  for (; i < url.length; i++) {
    const charCode = url.charCodeAt(i);
    if (charCode === 37) {
      const queryIndex = url.indexOf("?", i);
      const hashIndex = url.indexOf("#", i);
      const end = queryIndex === -1 ? hashIndex === -1 ? void 0 : hashIndex : hashIndex === -1 ? queryIndex : Math.min(queryIndex, hashIndex);
      const path = url.slice(start, end);
      return tryDecodeURI(path.includes("%25") ? path.replace(/%25/g, "%2525") : path);
    } else if (charCode === 63 || charCode === 35) {
      break;
    }
  }
  return url.slice(start, i);
};
var getPathNoStrict = (request) => {
  const result = getPath(request);
  return result.length > 1 && result.at(-1) === "/" ? result.slice(0, -1) : result;
};
var mergePath = (base, sub, ...rest) => {
  if (rest.length) {
    sub = mergePath(sub, ...rest);
  }
  return `${base?.[0] === "/" ? "" : "/"}${base}${sub === "/" ? "" : `${base?.at(-1) === "/" ? "" : "/"}${sub?.[0] === "/" ? sub.slice(1) : sub}`}`;
};
var checkOptionalParameter = (path) => {
  if (path.charCodeAt(path.length - 1) !== 63 || !path.includes(":")) {
    return null;
  }
  const segments = path.split("/");
  const results = [];
  let basePath2 = "";
  segments.forEach((segment) => {
    if (segment !== "" && !/\:/.test(segment)) {
      basePath2 += "/" + segment;
    } else if (/\:/.test(segment)) {
      if (/\?/.test(segment)) {
        if (results.length === 0 && basePath2 === "") {
          results.push("/");
        } else {
          results.push(basePath2);
        }
        const optionalSegment = segment.replace("?", "");
        basePath2 += "/" + optionalSegment;
        results.push(basePath2);
      } else {
        basePath2 += "/" + segment;
      }
    }
  });
  return results.filter((v, i, a) => a.indexOf(v) === i);
};
var _decodeURI = (value) => {
  if (!/[%+]/.test(value)) {
    return value;
  }
  if (value.indexOf("+") !== -1) {
    value = value.replace(/\+/g, " ");
  }
  return value.indexOf("%") !== -1 ? tryDecode(value, decodeURIComponent_) : value;
};
var _getQueryParam = (url, key, multiple) => {
  let encoded;
  if (!multiple && key && !/[%+]/.test(key)) {
    let keyIndex2 = url.indexOf("?", 8);
    if (keyIndex2 === -1) {
      return void 0;
    }
    if (!url.startsWith(key, keyIndex2 + 1)) {
      keyIndex2 = url.indexOf(`&${key}`, keyIndex2 + 1);
    }
    while (keyIndex2 !== -1) {
      const trailingKeyCode = url.charCodeAt(keyIndex2 + key.length + 1);
      if (trailingKeyCode === 61) {
        const valueIndex = keyIndex2 + key.length + 2;
        const endIndex = url.indexOf("&", valueIndex);
        return _decodeURI(url.slice(valueIndex, endIndex === -1 ? void 0 : endIndex));
      } else if (trailingKeyCode == 38 || isNaN(trailingKeyCode)) {
        return "";
      }
      keyIndex2 = url.indexOf(`&${key}`, keyIndex2 + 1);
    }
    encoded = /[%+]/.test(url);
    if (!encoded) {
      return void 0;
    }
  }
  const results = {};
  encoded ??= /[%+]/.test(url);
  let keyIndex = url.indexOf("?", 8);
  while (keyIndex !== -1) {
    const nextKeyIndex = url.indexOf("&", keyIndex + 1);
    let valueIndex = url.indexOf("=", keyIndex);
    if (valueIndex > nextKeyIndex && nextKeyIndex !== -1) {
      valueIndex = -1;
    }
    let name = url.slice(
      keyIndex + 1,
      valueIndex === -1 ? nextKeyIndex === -1 ? void 0 : nextKeyIndex : valueIndex
    );
    if (encoded) {
      name = _decodeURI(name);
    }
    keyIndex = nextKeyIndex;
    if (name === "") {
      continue;
    }
    let value;
    if (valueIndex === -1) {
      value = "";
    } else {
      value = url.slice(valueIndex + 1, nextKeyIndex === -1 ? void 0 : nextKeyIndex);
      if (encoded) {
        value = _decodeURI(value);
      }
    }
    if (multiple) {
      if (!(results[name] && Array.isArray(results[name]))) {
        results[name] = [];
      }
      ;
      results[name].push(value);
    } else {
      results[name] ??= value;
    }
  }
  return key ? results[key] : results;
};
var getQueryParam = _getQueryParam;
var getQueryParams = (url, key) => {
  return _getQueryParam(url, key, true);
};
var decodeURIComponent_ = decodeURIComponent;

// ../../node_modules/.pnpm/hono@4.12.5/node_modules/hono/dist/request.js
var tryDecodeURIComponent = (str) => tryDecode(str, decodeURIComponent_);
var HonoRequest = class {
  /**
   * `.raw` can get the raw Request object.
   *
   * @see {@link https://hono.dev/docs/api/request#raw}
   *
   * @example
   * ```ts
   * // For Cloudflare Workers
   * app.post('/', async (c) => {
   *   const metadata = c.req.raw.cf?.hostMetadata?
   *   ...
   * })
   * ```
   */
  raw;
  #validatedData;
  // Short name of validatedData
  #matchResult;
  routeIndex = 0;
  /**
   * `.path` can get the pathname of the request.
   *
   * @see {@link https://hono.dev/docs/api/request#path}
   *
   * @example
   * ```ts
   * app.get('/about/me', (c) => {
   *   const pathname = c.req.path // `/about/me`
   * })
   * ```
   */
  path;
  bodyCache = {};
  constructor(request, path = "/", matchResult = [[]]) {
    this.raw = request;
    this.path = path;
    this.#matchResult = matchResult;
    this.#validatedData = {};
  }
  param(key) {
    return key ? this.#getDecodedParam(key) : this.#getAllDecodedParams();
  }
  #getDecodedParam(key) {
    const paramKey = this.#matchResult[0][this.routeIndex][1][key];
    const param = this.#getParamValue(paramKey);
    return param && /\%/.test(param) ? tryDecodeURIComponent(param) : param;
  }
  #getAllDecodedParams() {
    const decoded = {};
    const keys = Object.keys(this.#matchResult[0][this.routeIndex][1]);
    for (const key of keys) {
      const value = this.#getParamValue(this.#matchResult[0][this.routeIndex][1][key]);
      if (value !== void 0) {
        decoded[key] = /\%/.test(value) ? tryDecodeURIComponent(value) : value;
      }
    }
    return decoded;
  }
  #getParamValue(paramKey) {
    return this.#matchResult[1] ? this.#matchResult[1][paramKey] : paramKey;
  }
  query(key) {
    return getQueryParam(this.url, key);
  }
  queries(key) {
    return getQueryParams(this.url, key);
  }
  header(name) {
    if (name) {
      return this.raw.headers.get(name) ?? void 0;
    }
    const headerData = {};
    this.raw.headers.forEach((value, key) => {
      headerData[key] = value;
    });
    return headerData;
  }
  async parseBody(options) {
    return this.bodyCache.parsedBody ??= await parseBody(this, options);
  }
  #cachedBody = (key) => {
    const { bodyCache, raw: raw2 } = this;
    const cachedBody = bodyCache[key];
    if (cachedBody) {
      return cachedBody;
    }
    const anyCachedKey = Object.keys(bodyCache)[0];
    if (anyCachedKey) {
      return bodyCache[anyCachedKey].then((body) => {
        if (anyCachedKey === "json") {
          body = JSON.stringify(body);
        }
        return new Response(body)[key]();
      });
    }
    return bodyCache[key] = raw2[key]();
  };
  /**
   * `.json()` can parse Request body of type `application/json`
   *
   * @see {@link https://hono.dev/docs/api/request#json}
   *
   * @example
   * ```ts
   * app.post('/entry', async (c) => {
   *   const body = await c.req.json()
   * })
   * ```
   */
  json() {
    return this.#cachedBody("text").then((text) => JSON.parse(text));
  }
  /**
   * `.text()` can parse Request body of type `text/plain`
   *
   * @see {@link https://hono.dev/docs/api/request#text}
   *
   * @example
   * ```ts
   * app.post('/entry', async (c) => {
   *   const body = await c.req.text()
   * })
   * ```
   */
  text() {
    return this.#cachedBody("text");
  }
  /**
   * `.arrayBuffer()` parse Request body as an `ArrayBuffer`
   *
   * @see {@link https://hono.dev/docs/api/request#arraybuffer}
   *
   * @example
   * ```ts
   * app.post('/entry', async (c) => {
   *   const body = await c.req.arrayBuffer()
   * })
   * ```
   */
  arrayBuffer() {
    return this.#cachedBody("arrayBuffer");
  }
  /**
   * Parses the request body as a `Blob`.
   * @example
   * ```ts
   * app.post('/entry', async (c) => {
   *   const body = await c.req.blob();
   * });
   * ```
   * @see https://hono.dev/docs/api/request#blob
   */
  blob() {
    return this.#cachedBody("blob");
  }
  /**
   * Parses the request body as `FormData`.
   * @example
   * ```ts
   * app.post('/entry', async (c) => {
   *   const body = await c.req.formData();
   * });
   * ```
   * @see https://hono.dev/docs/api/request#formdata
   */
  formData() {
    return this.#cachedBody("formData");
  }
  /**
   * Adds validated data to the request.
   *
   * @param target - The target of the validation.
   * @param data - The validated data to add.
   */
  addValidatedData(target, data) {
    this.#validatedData[target] = data;
  }
  valid(target) {
    return this.#validatedData[target];
  }
  /**
   * `.url()` can get the request url strings.
   *
   * @see {@link https://hono.dev/docs/api/request#url}
   *
   * @example
   * ```ts
   * app.get('/about/me', (c) => {
   *   const url = c.req.url // `http://localhost:8787/about/me`
   *   ...
   * })
   * ```
   */
  get url() {
    return this.raw.url;
  }
  /**
   * `.method()` can get the method name of the request.
   *
   * @see {@link https://hono.dev/docs/api/request#method}
   *
   * @example
   * ```ts
   * app.get('/about/me', (c) => {
   *   const method = c.req.method // `GET`
   * })
   * ```
   */
  get method() {
    return this.raw.method;
  }
  get [GET_MATCH_RESULT]() {
    return this.#matchResult;
  }
  /**
   * `.matchedRoutes()` can return a matched route in the handler
   *
   * @deprecated
   *
   * Use matchedRoutes helper defined in "hono/route" instead.
   *
   * @see {@link https://hono.dev/docs/api/request#matchedroutes}
   *
   * @example
   * ```ts
   * app.use('*', async function logger(c, next) {
   *   await next()
   *   c.req.matchedRoutes.forEach(({ handler, method, path }, i) => {
   *     const name = handler.name || (handler.length < 2 ? '[handler]' : '[middleware]')
   *     console.log(
   *       method,
   *       ' ',
   *       path,
   *       ' '.repeat(Math.max(10 - path.length, 0)),
   *       name,
   *       i === c.req.routeIndex ? '<- respond from here' : ''
   *     )
   *   })
   * })
   * ```
   */
  get matchedRoutes() {
    return this.#matchResult[0].map(([[, route]]) => route);
  }
  /**
   * `routePath()` can retrieve the path registered within the handler
   *
   * @deprecated
   *
   * Use routePath helper defined in "hono/route" instead.
   *
   * @see {@link https://hono.dev/docs/api/request#routepath}
   *
   * @example
   * ```ts
   * app.get('/posts/:id', (c) => {
   *   return c.json({ path: c.req.routePath })
   * })
   * ```
   */
  get routePath() {
    return this.#matchResult[0].map(([[, route]]) => route)[this.routeIndex].path;
  }
};

// ../../node_modules/.pnpm/hono@4.12.5/node_modules/hono/dist/utils/html.js
var HtmlEscapedCallbackPhase = {
  Stringify: 1,
  BeforeStream: 2,
  Stream: 3
};
var raw = (value, callbacks) => {
  const escapedString = new String(value);
  escapedString.isEscaped = true;
  escapedString.callbacks = callbacks;
  return escapedString;
};
var resolveCallback = async (str, phase, preserveCallbacks, context, buffer) => {
  if (typeof str === "object" && !(str instanceof String)) {
    if (!(str instanceof Promise)) {
      str = str.toString();
    }
    if (str instanceof Promise) {
      str = await str;
    }
  }
  const callbacks = str.callbacks;
  if (!callbacks?.length) {
    return Promise.resolve(str);
  }
  if (buffer) {
    buffer[0] += str;
  } else {
    buffer = [str];
  }
  const resStr = Promise.all(callbacks.map((c) => c({ phase, buffer, context }))).then(
    (res) => Promise.all(
      res.filter(Boolean).map((str2) => resolveCallback(str2, phase, false, context, buffer))
    ).then(() => buffer[0])
  );
  if (preserveCallbacks) {
    return raw(await resStr, callbacks);
  } else {
    return resStr;
  }
};

// ../../node_modules/.pnpm/hono@4.12.5/node_modules/hono/dist/context.js
var TEXT_PLAIN = "text/plain; charset=UTF-8";
var setDefaultContentType = (contentType, headers) => {
  return {
    "Content-Type": contentType,
    ...headers
  };
};
var createResponseInstance = (body, init) => new Response(body, init);
var Context = class {
  #rawRequest;
  #req;
  /**
   * `.env` can get bindings (environment variables, secrets, KV namespaces, D1 database, R2 bucket etc.) in Cloudflare Workers.
   *
   * @see {@link https://hono.dev/docs/api/context#env}
   *
   * @example
   * ```ts
   * // Environment object for Cloudflare Workers
   * app.get('*', async c => {
   *   const counter = c.env.COUNTER
   * })
   * ```
   */
  env = {};
  #var;
  finalized = false;
  /**
   * `.error` can get the error object from the middleware if the Handler throws an error.
   *
   * @see {@link https://hono.dev/docs/api/context#error}
   *
   * @example
   * ```ts
   * app.use('*', async (c, next) => {
   *   await next()
   *   if (c.error) {
   *     // do something...
   *   }
   * })
   * ```
   */
  error;
  #status;
  #executionCtx;
  #res;
  #layout;
  #renderer;
  #notFoundHandler;
  #preparedHeaders;
  #matchResult;
  #path;
  /**
   * Creates an instance of the Context class.
   *
   * @param req - The Request object.
   * @param options - Optional configuration options for the context.
   */
  constructor(req, options) {
    this.#rawRequest = req;
    if (options) {
      this.#executionCtx = options.executionCtx;
      this.env = options.env;
      this.#notFoundHandler = options.notFoundHandler;
      this.#path = options.path;
      this.#matchResult = options.matchResult;
    }
  }
  /**
   * `.req` is the instance of {@link HonoRequest}.
   */
  get req() {
    this.#req ??= new HonoRequest(this.#rawRequest, this.#path, this.#matchResult);
    return this.#req;
  }
  /**
   * @see {@link https://hono.dev/docs/api/context#event}
   * The FetchEvent associated with the current request.
   *
   * @throws Will throw an error if the context does not have a FetchEvent.
   */
  get event() {
    if (this.#executionCtx && "respondWith" in this.#executionCtx) {
      return this.#executionCtx;
    } else {
      throw Error("This context has no FetchEvent");
    }
  }
  /**
   * @see {@link https://hono.dev/docs/api/context#executionctx}
   * The ExecutionContext associated with the current request.
   *
   * @throws Will throw an error if the context does not have an ExecutionContext.
   */
  get executionCtx() {
    if (this.#executionCtx) {
      return this.#executionCtx;
    } else {
      throw Error("This context has no ExecutionContext");
    }
  }
  /**
   * @see {@link https://hono.dev/docs/api/context#res}
   * The Response object for the current request.
   */
  get res() {
    return this.#res ||= createResponseInstance(null, {
      headers: this.#preparedHeaders ??= new Headers()
    });
  }
  /**
   * Sets the Response object for the current request.
   *
   * @param _res - The Response object to set.
   */
  set res(_res) {
    if (this.#res && _res) {
      _res = createResponseInstance(_res.body, _res);
      for (const [k, v] of this.#res.headers.entries()) {
        if (k === "content-type") {
          continue;
        }
        if (k === "set-cookie") {
          const cookies = this.#res.headers.getSetCookie();
          _res.headers.delete("set-cookie");
          for (const cookie of cookies) {
            _res.headers.append("set-cookie", cookie);
          }
        } else {
          _res.headers.set(k, v);
        }
      }
    }
    this.#res = _res;
    this.finalized = true;
  }
  /**
   * `.render()` can create a response within a layout.
   *
   * @see {@link https://hono.dev/docs/api/context#render-setrenderer}
   *
   * @example
   * ```ts
   * app.get('/', (c) => {
   *   return c.render('Hello!')
   * })
   * ```
   */
  render = (...args) => {
    this.#renderer ??= (content) => this.html(content);
    return this.#renderer(...args);
  };
  /**
   * Sets the layout for the response.
   *
   * @param layout - The layout to set.
   * @returns The layout function.
   */
  setLayout = (layout) => this.#layout = layout;
  /**
   * Gets the current layout for the response.
   *
   * @returns The current layout function.
   */
  getLayout = () => this.#layout;
  /**
   * `.setRenderer()` can set the layout in the custom middleware.
   *
   * @see {@link https://hono.dev/docs/api/context#render-setrenderer}
   *
   * @example
   * ```tsx
   * app.use('*', async (c, next) => {
   *   c.setRenderer((content) => {
   *     return c.html(
   *       <html>
   *         <body>
   *           <p>{content}</p>
   *         </body>
   *       </html>
   *     )
   *   })
   *   await next()
   * })
   * ```
   */
  setRenderer = (renderer) => {
    this.#renderer = renderer;
  };
  /**
   * `.header()` can set headers.
   *
   * @see {@link https://hono.dev/docs/api/context#header}
   *
   * @example
   * ```ts
   * app.get('/welcome', (c) => {
   *   // Set headers
   *   c.header('X-Message', 'Hello!')
   *   c.header('Content-Type', 'text/plain')
   *
   *   return c.body('Thank you for coming')
   * })
   * ```
   */
  header = (name, value, options) => {
    if (this.finalized) {
      this.#res = createResponseInstance(this.#res.body, this.#res);
    }
    const headers = this.#res ? this.#res.headers : this.#preparedHeaders ??= new Headers();
    if (value === void 0) {
      headers.delete(name);
    } else if (options?.append) {
      headers.append(name, value);
    } else {
      headers.set(name, value);
    }
  };
  status = (status) => {
    this.#status = status;
  };
  /**
   * `.set()` can set the value specified by the key.
   *
   * @see {@link https://hono.dev/docs/api/context#set-get}
   *
   * @example
   * ```ts
   * app.use('*', async (c, next) => {
   *   c.set('message', 'Hono is hot!!')
   *   await next()
   * })
   * ```
   */
  set = (key, value) => {
    this.#var ??= /* @__PURE__ */ new Map();
    this.#var.set(key, value);
  };
  /**
   * `.get()` can use the value specified by the key.
   *
   * @see {@link https://hono.dev/docs/api/context#set-get}
   *
   * @example
   * ```ts
   * app.get('/', (c) => {
   *   const message = c.get('message')
   *   return c.text(`The message is "${message}"`)
   * })
   * ```
   */
  get = (key) => {
    return this.#var ? this.#var.get(key) : void 0;
  };
  /**
   * `.var` can access the value of a variable.
   *
   * @see {@link https://hono.dev/docs/api/context#var}
   *
   * @example
   * ```ts
   * const result = c.var.client.oneMethod()
   * ```
   */
  // c.var.propName is a read-only
  get var() {
    if (!this.#var) {
      return {};
    }
    return Object.fromEntries(this.#var);
  }
  #newResponse(data, arg, headers) {
    const responseHeaders = this.#res ? new Headers(this.#res.headers) : this.#preparedHeaders ?? new Headers();
    if (typeof arg === "object" && "headers" in arg) {
      const argHeaders = arg.headers instanceof Headers ? arg.headers : new Headers(arg.headers);
      for (const [key, value] of argHeaders) {
        if (key.toLowerCase() === "set-cookie") {
          responseHeaders.append(key, value);
        } else {
          responseHeaders.set(key, value);
        }
      }
    }
    if (headers) {
      for (const [k, v] of Object.entries(headers)) {
        if (typeof v === "string") {
          responseHeaders.set(k, v);
        } else {
          responseHeaders.delete(k);
          for (const v2 of v) {
            responseHeaders.append(k, v2);
          }
        }
      }
    }
    const status = typeof arg === "number" ? arg : arg?.status ?? this.#status;
    return createResponseInstance(data, { status, headers: responseHeaders });
  }
  newResponse = (...args) => this.#newResponse(...args);
  /**
   * `.body()` can return the HTTP response.
   * You can set headers with `.header()` and set HTTP status code with `.status`.
   * This can also be set in `.text()`, `.json()` and so on.
   *
   * @see {@link https://hono.dev/docs/api/context#body}
   *
   * @example
   * ```ts
   * app.get('/welcome', (c) => {
   *   // Set headers
   *   c.header('X-Message', 'Hello!')
   *   c.header('Content-Type', 'text/plain')
   *   // Set HTTP status code
   *   c.status(201)
   *
   *   // Return the response body
   *   return c.body('Thank you for coming')
   * })
   * ```
   */
  body = (data, arg, headers) => this.#newResponse(data, arg, headers);
  /**
   * `.text()` can render text as `Content-Type:text/plain`.
   *
   * @see {@link https://hono.dev/docs/api/context#text}
   *
   * @example
   * ```ts
   * app.get('/say', (c) => {
   *   return c.text('Hello!')
   * })
   * ```
   */
  text = (text, arg, headers) => {
    return !this.#preparedHeaders && !this.#status && !arg && !headers && !this.finalized ? new Response(text) : this.#newResponse(
      text,
      arg,
      setDefaultContentType(TEXT_PLAIN, headers)
    );
  };
  /**
   * `.json()` can render JSON as `Content-Type:application/json`.
   *
   * @see {@link https://hono.dev/docs/api/context#json}
   *
   * @example
   * ```ts
   * app.get('/api', (c) => {
   *   return c.json({ message: 'Hello!' })
   * })
   * ```
   */
  json = (object, arg, headers) => {
    return this.#newResponse(
      JSON.stringify(object),
      arg,
      setDefaultContentType("application/json", headers)
    );
  };
  html = (html, arg, headers) => {
    const res = (html2) => this.#newResponse(html2, arg, setDefaultContentType("text/html; charset=UTF-8", headers));
    return typeof html === "object" ? resolveCallback(html, HtmlEscapedCallbackPhase.Stringify, false, {}).then(res) : res(html);
  };
  /**
   * `.redirect()` can Redirect, default status code is 302.
   *
   * @see {@link https://hono.dev/docs/api/context#redirect}
   *
   * @example
   * ```ts
   * app.get('/redirect', (c) => {
   *   return c.redirect('/')
   * })
   * app.get('/redirect-permanently', (c) => {
   *   return c.redirect('/', 301)
   * })
   * ```
   */
  redirect = (location, status) => {
    const locationString = String(location);
    this.header(
      "Location",
      // Multibyes should be encoded
      // eslint-disable-next-line no-control-regex
      !/[^\x00-\xFF]/.test(locationString) ? locationString : encodeURI(locationString)
    );
    return this.newResponse(null, status ?? 302);
  };
  /**
   * `.notFound()` can return the Not Found Response.
   *
   * @see {@link https://hono.dev/docs/api/context#notfound}
   *
   * @example
   * ```ts
   * app.get('/notfound', (c) => {
   *   return c.notFound()
   * })
   * ```
   */
  notFound = () => {
    this.#notFoundHandler ??= () => createResponseInstance();
    return this.#notFoundHandler(this);
  };
};

// ../../node_modules/.pnpm/hono@4.12.5/node_modules/hono/dist/router.js
var METHOD_NAME_ALL = "ALL";
var METHOD_NAME_ALL_LOWERCASE = "all";
var METHODS = ["get", "post", "put", "delete", "options", "patch"];
var MESSAGE_MATCHER_IS_ALREADY_BUILT = "Can not add a route since the matcher is already built.";
var UnsupportedPathError = class extends Error {
};

// ../../node_modules/.pnpm/hono@4.12.5/node_modules/hono/dist/utils/constants.js
var COMPOSED_HANDLER = "__COMPOSED_HANDLER";

// ../../node_modules/.pnpm/hono@4.12.5/node_modules/hono/dist/hono-base.js
var notFoundHandler = (c) => {
  return c.text("404 Not Found", 404);
};
var errorHandler = (err, c) => {
  if ("getResponse" in err) {
    const res = err.getResponse();
    return c.newResponse(res.body, res);
  }
  console.error(err);
  return c.text("Internal Server Error", 500);
};
var Hono = class _Hono {
  get;
  post;
  put;
  delete;
  options;
  patch;
  all;
  on;
  use;
  /*
    This class is like an abstract class and does not have a router.
    To use it, inherit the class and implement router in the constructor.
  */
  router;
  getPath;
  // Cannot use `#` because it requires visibility at JavaScript runtime.
  _basePath = "/";
  #path = "/";
  routes = [];
  constructor(options = {}) {
    const allMethods = [...METHODS, METHOD_NAME_ALL_LOWERCASE];
    allMethods.forEach((method) => {
      this[method] = (args1, ...args) => {
        if (typeof args1 === "string") {
          this.#path = args1;
        } else {
          this.#addRoute(method, this.#path, args1);
        }
        args.forEach((handler) => {
          this.#addRoute(method, this.#path, handler);
        });
        return this;
      };
    });
    this.on = (method, path, ...handlers) => {
      for (const p of [path].flat()) {
        this.#path = p;
        for (const m of [method].flat()) {
          handlers.map((handler) => {
            this.#addRoute(m.toUpperCase(), this.#path, handler);
          });
        }
      }
      return this;
    };
    this.use = (arg1, ...handlers) => {
      if (typeof arg1 === "string") {
        this.#path = arg1;
      } else {
        this.#path = "*";
        handlers.unshift(arg1);
      }
      handlers.forEach((handler) => {
        this.#addRoute(METHOD_NAME_ALL, this.#path, handler);
      });
      return this;
    };
    const { strict, ...optionsWithoutStrict } = options;
    Object.assign(this, optionsWithoutStrict);
    this.getPath = strict ?? true ? options.getPath ?? getPath : getPathNoStrict;
  }
  #clone() {
    const clone = new _Hono({
      router: this.router,
      getPath: this.getPath
    });
    clone.errorHandler = this.errorHandler;
    clone.#notFoundHandler = this.#notFoundHandler;
    clone.routes = this.routes;
    return clone;
  }
  #notFoundHandler = notFoundHandler;
  // Cannot use `#` because it requires visibility at JavaScript runtime.
  errorHandler = errorHandler;
  /**
   * `.route()` allows grouping other Hono instance in routes.
   *
   * @see {@link https://hono.dev/docs/api/routing#grouping}
   *
   * @param {string} path - base Path
   * @param {Hono} app - other Hono instance
   * @returns {Hono} routed Hono instance
   *
   * @example
   * ```ts
   * const app = new Hono()
   * const app2 = new Hono()
   *
   * app2.get("/user", (c) => c.text("user"))
   * app.route("/api", app2) // GET /api/user
   * ```
   */
  route(path, app7) {
    const subApp = this.basePath(path);
    app7.routes.map((r) => {
      let handler;
      if (app7.errorHandler === errorHandler) {
        handler = r.handler;
      } else {
        handler = async (c, next) => (await compose([], app7.errorHandler)(c, () => r.handler(c, next))).res;
        handler[COMPOSED_HANDLER] = r.handler;
      }
      subApp.#addRoute(r.method, r.path, handler);
    });
    return this;
  }
  /**
   * `.basePath()` allows base paths to be specified.
   *
   * @see {@link https://hono.dev/docs/api/routing#base-path}
   *
   * @param {string} path - base Path
   * @returns {Hono} changed Hono instance
   *
   * @example
   * ```ts
   * const api = new Hono().basePath('/api')
   * ```
   */
  basePath(path) {
    const subApp = this.#clone();
    subApp._basePath = mergePath(this._basePath, path);
    return subApp;
  }
  /**
   * `.onError()` handles an error and returns a customized Response.
   *
   * @see {@link https://hono.dev/docs/api/hono#error-handling}
   *
   * @param {ErrorHandler} handler - request Handler for error
   * @returns {Hono} changed Hono instance
   *
   * @example
   * ```ts
   * app.onError((err, c) => {
   *   console.error(`${err}`)
   *   return c.text('Custom Error Message', 500)
   * })
   * ```
   */
  onError = (handler) => {
    this.errorHandler = handler;
    return this;
  };
  /**
   * `.notFound()` allows you to customize a Not Found Response.
   *
   * @see {@link https://hono.dev/docs/api/hono#not-found}
   *
   * @param {NotFoundHandler} handler - request handler for not-found
   * @returns {Hono} changed Hono instance
   *
   * @example
   * ```ts
   * app.notFound((c) => {
   *   return c.text('Custom 404 Message', 404)
   * })
   * ```
   */
  notFound = (handler) => {
    this.#notFoundHandler = handler;
    return this;
  };
  /**
   * `.mount()` allows you to mount applications built with other frameworks into your Hono application.
   *
   * @see {@link https://hono.dev/docs/api/hono#mount}
   *
   * @param {string} path - base Path
   * @param {Function} applicationHandler - other Request Handler
   * @param {MountOptions} [options] - options of `.mount()`
   * @returns {Hono} mounted Hono instance
   *
   * @example
   * ```ts
   * import { Router as IttyRouter } from 'itty-router'
   * import { Hono } from 'hono'
   * // Create itty-router application
   * const ittyRouter = IttyRouter()
   * // GET /itty-router/hello
   * ittyRouter.get('/hello', () => new Response('Hello from itty-router'))
   *
   * const app = new Hono()
   * app.mount('/itty-router', ittyRouter.handle)
   * ```
   *
   * @example
   * ```ts
   * const app = new Hono()
   * // Send the request to another application without modification.
   * app.mount('/app', anotherApp, {
   *   replaceRequest: (req) => req,
   * })
   * ```
   */
  mount(path, applicationHandler, options) {
    let replaceRequest;
    let optionHandler;
    if (options) {
      if (typeof options === "function") {
        optionHandler = options;
      } else {
        optionHandler = options.optionHandler;
        if (options.replaceRequest === false) {
          replaceRequest = (request) => request;
        } else {
          replaceRequest = options.replaceRequest;
        }
      }
    }
    const getOptions = optionHandler ? (c) => {
      const options2 = optionHandler(c);
      return Array.isArray(options2) ? options2 : [options2];
    } : (c) => {
      let executionContext = void 0;
      try {
        executionContext = c.executionCtx;
      } catch {
      }
      return [c.env, executionContext];
    };
    replaceRequest ||= (() => {
      const mergedPath = mergePath(this._basePath, path);
      const pathPrefixLength = mergedPath === "/" ? 0 : mergedPath.length;
      return (request) => {
        const url = new URL(request.url);
        url.pathname = url.pathname.slice(pathPrefixLength) || "/";
        return new Request(url, request);
      };
    })();
    const handler = async (c, next) => {
      const res = await applicationHandler(replaceRequest(c.req.raw), ...getOptions(c));
      if (res) {
        return res;
      }
      await next();
    };
    this.#addRoute(METHOD_NAME_ALL, mergePath(path, "*"), handler);
    return this;
  }
  #addRoute(method, path, handler) {
    method = method.toUpperCase();
    path = mergePath(this._basePath, path);
    const r = { basePath: this._basePath, path, method, handler };
    this.router.add(method, path, [handler, r]);
    this.routes.push(r);
  }
  #handleError(err, c) {
    if (err instanceof Error) {
      return this.errorHandler(err, c);
    }
    throw err;
  }
  #dispatch(request, executionCtx, env, method) {
    if (method === "HEAD") {
      return (async () => new Response(null, await this.#dispatch(request, executionCtx, env, "GET")))();
    }
    const path = this.getPath(request, { env });
    const matchResult = this.router.match(method, path);
    const c = new Context(request, {
      path,
      matchResult,
      env,
      executionCtx,
      notFoundHandler: this.#notFoundHandler
    });
    if (matchResult[0].length === 1) {
      let res;
      try {
        res = matchResult[0][0][0][0](c, async () => {
          c.res = await this.#notFoundHandler(c);
        });
      } catch (err) {
        return this.#handleError(err, c);
      }
      return res instanceof Promise ? res.then(
        (resolved) => resolved || (c.finalized ? c.res : this.#notFoundHandler(c))
      ).catch((err) => this.#handleError(err, c)) : res ?? this.#notFoundHandler(c);
    }
    const composed = compose(matchResult[0], this.errorHandler, this.#notFoundHandler);
    return (async () => {
      try {
        const context = await composed(c);
        if (!context.finalized) {
          throw new Error(
            "Context is not finalized. Did you forget to return a Response object or `await next()`?"
          );
        }
        return context.res;
      } catch (err) {
        return this.#handleError(err, c);
      }
    })();
  }
  /**
   * `.fetch()` will be entry point of your app.
   *
   * @see {@link https://hono.dev/docs/api/hono#fetch}
   *
   * @param {Request} request - request Object of request
   * @param {Env} Env - env Object
   * @param {ExecutionContext} - context of execution
   * @returns {Response | Promise<Response>} response of request
   *
   */
  fetch = (request, ...rest) => {
    return this.#dispatch(request, rest[1], rest[0], request.method);
  };
  /**
   * `.request()` is a useful method for testing.
   * You can pass a URL or pathname to send a GET request.
   * app will return a Response object.
   * ```ts
   * test('GET /hello is ok', async () => {
   *   const res = await app.request('/hello')
   *   expect(res.status).toBe(200)
   * })
   * ```
   * @see https://hono.dev/docs/api/hono#request
   */
  request = (input, requestInit, Env, executionCtx) => {
    if (input instanceof Request) {
      return this.fetch(requestInit ? new Request(input, requestInit) : input, Env, executionCtx);
    }
    input = input.toString();
    return this.fetch(
      new Request(
        /^https?:\/\//.test(input) ? input : `http://localhost${mergePath("/", input)}`,
        requestInit
      ),
      Env,
      executionCtx
    );
  };
  /**
   * `.fire()` automatically adds a global fetch event listener.
   * This can be useful for environments that adhere to the Service Worker API, such as non-ES module Cloudflare Workers.
   * @deprecated
   * Use `fire` from `hono/service-worker` instead.
   * ```ts
   * import { Hono } from 'hono'
   * import { fire } from 'hono/service-worker'
   *
   * const app = new Hono()
   * // ...
   * fire(app)
   * ```
   * @see https://hono.dev/docs/api/hono#fire
   * @see https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API
   * @see https://developers.cloudflare.com/workers/reference/migrate-to-module-workers/
   */
  fire = () => {
    addEventListener("fetch", (event) => {
      event.respondWith(this.#dispatch(event.request, event, void 0, event.request.method));
    });
  };
};

// ../../node_modules/.pnpm/hono@4.12.5/node_modules/hono/dist/router/reg-exp-router/matcher.js
var emptyParam = [];
function match(method, path) {
  const matchers = this.buildAllMatchers();
  const match2 = ((method2, path2) => {
    const matcher = matchers[method2] || matchers[METHOD_NAME_ALL];
    const staticMatch = matcher[2][path2];
    if (staticMatch) {
      return staticMatch;
    }
    const match3 = path2.match(matcher[0]);
    if (!match3) {
      return [[], emptyParam];
    }
    const index = match3.indexOf("", 1);
    return [matcher[1][index], match3];
  });
  this.match = match2;
  return match2(method, path);
}

// ../../node_modules/.pnpm/hono@4.12.5/node_modules/hono/dist/router/reg-exp-router/node.js
var LABEL_REG_EXP_STR = "[^/]+";
var ONLY_WILDCARD_REG_EXP_STR = ".*";
var TAIL_WILDCARD_REG_EXP_STR = "(?:|/.*)";
var PATH_ERROR = /* @__PURE__ */ Symbol();
var regExpMetaChars = new Set(".\\+*[^]$()");
function compareKey(a, b) {
  if (a.length === 1) {
    return b.length === 1 ? a < b ? -1 : 1 : -1;
  }
  if (b.length === 1) {
    return 1;
  }
  if (a === ONLY_WILDCARD_REG_EXP_STR || a === TAIL_WILDCARD_REG_EXP_STR) {
    return 1;
  } else if (b === ONLY_WILDCARD_REG_EXP_STR || b === TAIL_WILDCARD_REG_EXP_STR) {
    return -1;
  }
  if (a === LABEL_REG_EXP_STR) {
    return 1;
  } else if (b === LABEL_REG_EXP_STR) {
    return -1;
  }
  return a.length === b.length ? a < b ? -1 : 1 : b.length - a.length;
}
var Node = class _Node {
  #index;
  #varIndex;
  #children = /* @__PURE__ */ Object.create(null);
  insert(tokens, index, paramMap, context, pathErrorCheckOnly) {
    if (tokens.length === 0) {
      if (this.#index !== void 0) {
        throw PATH_ERROR;
      }
      if (pathErrorCheckOnly) {
        return;
      }
      this.#index = index;
      return;
    }
    const [token, ...restTokens] = tokens;
    const pattern = token === "*" ? restTokens.length === 0 ? ["", "", ONLY_WILDCARD_REG_EXP_STR] : ["", "", LABEL_REG_EXP_STR] : token === "/*" ? ["", "", TAIL_WILDCARD_REG_EXP_STR] : token.match(/^\:([^\{\}]+)(?:\{(.+)\})?$/);
    let node;
    if (pattern) {
      const name = pattern[1];
      let regexpStr = pattern[2] || LABEL_REG_EXP_STR;
      if (name && pattern[2]) {
        if (regexpStr === ".*") {
          throw PATH_ERROR;
        }
        regexpStr = regexpStr.replace(/^\((?!\?:)(?=[^)]+\)$)/, "(?:");
        if (/\((?!\?:)/.test(regexpStr)) {
          throw PATH_ERROR;
        }
      }
      node = this.#children[regexpStr];
      if (!node) {
        if (Object.keys(this.#children).some(
          (k) => k !== ONLY_WILDCARD_REG_EXP_STR && k !== TAIL_WILDCARD_REG_EXP_STR
        )) {
          throw PATH_ERROR;
        }
        if (pathErrorCheckOnly) {
          return;
        }
        node = this.#children[regexpStr] = new _Node();
        if (name !== "") {
          node.#varIndex = context.varIndex++;
        }
      }
      if (!pathErrorCheckOnly && name !== "") {
        paramMap.push([name, node.#varIndex]);
      }
    } else {
      node = this.#children[token];
      if (!node) {
        if (Object.keys(this.#children).some(
          (k) => k.length > 1 && k !== ONLY_WILDCARD_REG_EXP_STR && k !== TAIL_WILDCARD_REG_EXP_STR
        )) {
          throw PATH_ERROR;
        }
        if (pathErrorCheckOnly) {
          return;
        }
        node = this.#children[token] = new _Node();
      }
    }
    node.insert(restTokens, index, paramMap, context, pathErrorCheckOnly);
  }
  buildRegExpStr() {
    const childKeys = Object.keys(this.#children).sort(compareKey);
    const strList = childKeys.map((k) => {
      const c = this.#children[k];
      return (typeof c.#varIndex === "number" ? `(${k})@${c.#varIndex}` : regExpMetaChars.has(k) ? `\\${k}` : k) + c.buildRegExpStr();
    });
    if (typeof this.#index === "number") {
      strList.unshift(`#${this.#index}`);
    }
    if (strList.length === 0) {
      return "";
    }
    if (strList.length === 1) {
      return strList[0];
    }
    return "(?:" + strList.join("|") + ")";
  }
};

// ../../node_modules/.pnpm/hono@4.12.5/node_modules/hono/dist/router/reg-exp-router/trie.js
var Trie = class {
  #context = { varIndex: 0 };
  #root = new Node();
  insert(path, index, pathErrorCheckOnly) {
    const paramAssoc = [];
    const groups = [];
    for (let i = 0; ; ) {
      let replaced = false;
      path = path.replace(/\{[^}]+\}/g, (m) => {
        const mark = `@\\${i}`;
        groups[i] = [mark, m];
        i++;
        replaced = true;
        return mark;
      });
      if (!replaced) {
        break;
      }
    }
    const tokens = path.match(/(?::[^\/]+)|(?:\/\*$)|./g) || [];
    for (let i = groups.length - 1; i >= 0; i--) {
      const [mark] = groups[i];
      for (let j = tokens.length - 1; j >= 0; j--) {
        if (tokens[j].indexOf(mark) !== -1) {
          tokens[j] = tokens[j].replace(mark, groups[i][1]);
          break;
        }
      }
    }
    this.#root.insert(tokens, index, paramAssoc, this.#context, pathErrorCheckOnly);
    return paramAssoc;
  }
  buildRegExp() {
    let regexp = this.#root.buildRegExpStr();
    if (regexp === "") {
      return [/^$/, [], []];
    }
    let captureIndex = 0;
    const indexReplacementMap = [];
    const paramReplacementMap = [];
    regexp = regexp.replace(/#(\d+)|@(\d+)|\.\*\$/g, (_, handlerIndex, paramIndex) => {
      if (handlerIndex !== void 0) {
        indexReplacementMap[++captureIndex] = Number(handlerIndex);
        return "$()";
      }
      if (paramIndex !== void 0) {
        paramReplacementMap[Number(paramIndex)] = ++captureIndex;
        return "";
      }
      return "";
    });
    return [new RegExp(`^${regexp}`), indexReplacementMap, paramReplacementMap];
  }
};

// ../../node_modules/.pnpm/hono@4.12.5/node_modules/hono/dist/router/reg-exp-router/router.js
var nullMatcher = [/^$/, [], /* @__PURE__ */ Object.create(null)];
var wildcardRegExpCache = /* @__PURE__ */ Object.create(null);
function buildWildcardRegExp(path) {
  return wildcardRegExpCache[path] ??= new RegExp(
    path === "*" ? "" : `^${path.replace(
      /\/\*$|([.\\+*[^\]$()])/g,
      (_, metaChar) => metaChar ? `\\${metaChar}` : "(?:|/.*)"
    )}$`
  );
}
function clearWildcardRegExpCache() {
  wildcardRegExpCache = /* @__PURE__ */ Object.create(null);
}
function buildMatcherFromPreprocessedRoutes(routes) {
  const trie = new Trie();
  const handlerData = [];
  if (routes.length === 0) {
    return nullMatcher;
  }
  const routesWithStaticPathFlag = routes.map(
    (route) => [!/\*|\/:/.test(route[0]), ...route]
  ).sort(
    ([isStaticA, pathA], [isStaticB, pathB]) => isStaticA ? 1 : isStaticB ? -1 : pathA.length - pathB.length
  );
  const staticMap = /* @__PURE__ */ Object.create(null);
  for (let i = 0, j = -1, len = routesWithStaticPathFlag.length; i < len; i++) {
    const [pathErrorCheckOnly, path, handlers] = routesWithStaticPathFlag[i];
    if (pathErrorCheckOnly) {
      staticMap[path] = [handlers.map(([h]) => [h, /* @__PURE__ */ Object.create(null)]), emptyParam];
    } else {
      j++;
    }
    let paramAssoc;
    try {
      paramAssoc = trie.insert(path, j, pathErrorCheckOnly);
    } catch (e) {
      throw e === PATH_ERROR ? new UnsupportedPathError(path) : e;
    }
    if (pathErrorCheckOnly) {
      continue;
    }
    handlerData[j] = handlers.map(([h, paramCount]) => {
      const paramIndexMap = /* @__PURE__ */ Object.create(null);
      paramCount -= 1;
      for (; paramCount >= 0; paramCount--) {
        const [key, value] = paramAssoc[paramCount];
        paramIndexMap[key] = value;
      }
      return [h, paramIndexMap];
    });
  }
  const [regexp, indexReplacementMap, paramReplacementMap] = trie.buildRegExp();
  for (let i = 0, len = handlerData.length; i < len; i++) {
    for (let j = 0, len2 = handlerData[i].length; j < len2; j++) {
      const map = handlerData[i][j]?.[1];
      if (!map) {
        continue;
      }
      const keys = Object.keys(map);
      for (let k = 0, len3 = keys.length; k < len3; k++) {
        map[keys[k]] = paramReplacementMap[map[keys[k]]];
      }
    }
  }
  const handlerMap = [];
  for (const i in indexReplacementMap) {
    handlerMap[i] = handlerData[indexReplacementMap[i]];
  }
  return [regexp, handlerMap, staticMap];
}
function findMiddleware(middleware, path) {
  if (!middleware) {
    return void 0;
  }
  for (const k of Object.keys(middleware).sort((a, b) => b.length - a.length)) {
    if (buildWildcardRegExp(k).test(path)) {
      return [...middleware[k]];
    }
  }
  return void 0;
}
var RegExpRouter = class {
  name = "RegExpRouter";
  #middleware;
  #routes;
  constructor() {
    this.#middleware = { [METHOD_NAME_ALL]: /* @__PURE__ */ Object.create(null) };
    this.#routes = { [METHOD_NAME_ALL]: /* @__PURE__ */ Object.create(null) };
  }
  add(method, path, handler) {
    const middleware = this.#middleware;
    const routes = this.#routes;
    if (!middleware || !routes) {
      throw new Error(MESSAGE_MATCHER_IS_ALREADY_BUILT);
    }
    if (!middleware[method]) {
      ;
      [middleware, routes].forEach((handlerMap) => {
        handlerMap[method] = /* @__PURE__ */ Object.create(null);
        Object.keys(handlerMap[METHOD_NAME_ALL]).forEach((p) => {
          handlerMap[method][p] = [...handlerMap[METHOD_NAME_ALL][p]];
        });
      });
    }
    if (path === "/*") {
      path = "*";
    }
    const paramCount = (path.match(/\/:/g) || []).length;
    if (/\*$/.test(path)) {
      const re = buildWildcardRegExp(path);
      if (method === METHOD_NAME_ALL) {
        Object.keys(middleware).forEach((m) => {
          middleware[m][path] ||= findMiddleware(middleware[m], path) || findMiddleware(middleware[METHOD_NAME_ALL], path) || [];
        });
      } else {
        middleware[method][path] ||= findMiddleware(middleware[method], path) || findMiddleware(middleware[METHOD_NAME_ALL], path) || [];
      }
      Object.keys(middleware).forEach((m) => {
        if (method === METHOD_NAME_ALL || method === m) {
          Object.keys(middleware[m]).forEach((p) => {
            re.test(p) && middleware[m][p].push([handler, paramCount]);
          });
        }
      });
      Object.keys(routes).forEach((m) => {
        if (method === METHOD_NAME_ALL || method === m) {
          Object.keys(routes[m]).forEach(
            (p) => re.test(p) && routes[m][p].push([handler, paramCount])
          );
        }
      });
      return;
    }
    const paths = checkOptionalParameter(path) || [path];
    for (let i = 0, len = paths.length; i < len; i++) {
      const path2 = paths[i];
      Object.keys(routes).forEach((m) => {
        if (method === METHOD_NAME_ALL || method === m) {
          routes[m][path2] ||= [
            ...findMiddleware(middleware[m], path2) || findMiddleware(middleware[METHOD_NAME_ALL], path2) || []
          ];
          routes[m][path2].push([handler, paramCount - len + i + 1]);
        }
      });
    }
  }
  match = match;
  buildAllMatchers() {
    const matchers = /* @__PURE__ */ Object.create(null);
    Object.keys(this.#routes).concat(Object.keys(this.#middleware)).forEach((method) => {
      matchers[method] ||= this.#buildMatcher(method);
    });
    this.#middleware = this.#routes = void 0;
    clearWildcardRegExpCache();
    return matchers;
  }
  #buildMatcher(method) {
    const routes = [];
    let hasOwnRoute = method === METHOD_NAME_ALL;
    [this.#middleware, this.#routes].forEach((r) => {
      const ownRoute = r[method] ? Object.keys(r[method]).map((path) => [path, r[method][path]]) : [];
      if (ownRoute.length !== 0) {
        hasOwnRoute ||= true;
        routes.push(...ownRoute);
      } else if (method !== METHOD_NAME_ALL) {
        routes.push(
          ...Object.keys(r[METHOD_NAME_ALL]).map((path) => [path, r[METHOD_NAME_ALL][path]])
        );
      }
    });
    if (!hasOwnRoute) {
      return null;
    } else {
      return buildMatcherFromPreprocessedRoutes(routes);
    }
  }
};

// ../../node_modules/.pnpm/hono@4.12.5/node_modules/hono/dist/router/smart-router/router.js
var SmartRouter = class {
  name = "SmartRouter";
  #routers = [];
  #routes = [];
  constructor(init) {
    this.#routers = init.routers;
  }
  add(method, path, handler) {
    if (!this.#routes) {
      throw new Error(MESSAGE_MATCHER_IS_ALREADY_BUILT);
    }
    this.#routes.push([method, path, handler]);
  }
  match(method, path) {
    if (!this.#routes) {
      throw new Error("Fatal error");
    }
    const routers = this.#routers;
    const routes = this.#routes;
    const len = routers.length;
    let i = 0;
    let res;
    for (; i < len; i++) {
      const router = routers[i];
      try {
        for (let i2 = 0, len2 = routes.length; i2 < len2; i2++) {
          router.add(...routes[i2]);
        }
        res = router.match(method, path);
      } catch (e) {
        if (e instanceof UnsupportedPathError) {
          continue;
        }
        throw e;
      }
      this.match = router.match.bind(router);
      this.#routers = [router];
      this.#routes = void 0;
      break;
    }
    if (i === len) {
      throw new Error("Fatal error");
    }
    this.name = `SmartRouter + ${this.activeRouter.name}`;
    return res;
  }
  get activeRouter() {
    if (this.#routes || this.#routers.length !== 1) {
      throw new Error("No active router has been determined yet.");
    }
    return this.#routers[0];
  }
};

// ../../node_modules/.pnpm/hono@4.12.5/node_modules/hono/dist/router/trie-router/node.js
var emptyParams = /* @__PURE__ */ Object.create(null);
var hasChildren = (children) => {
  for (const _ in children) {
    return true;
  }
  return false;
};
var Node2 = class _Node2 {
  #methods;
  #children;
  #patterns;
  #order = 0;
  #params = emptyParams;
  constructor(method, handler, children) {
    this.#children = children || /* @__PURE__ */ Object.create(null);
    this.#methods = [];
    if (method && handler) {
      const m = /* @__PURE__ */ Object.create(null);
      m[method] = { handler, possibleKeys: [], score: 0 };
      this.#methods = [m];
    }
    this.#patterns = [];
  }
  insert(method, path, handler) {
    this.#order = ++this.#order;
    let curNode = this;
    const parts = splitRoutingPath(path);
    const possibleKeys = [];
    for (let i = 0, len = parts.length; i < len; i++) {
      const p = parts[i];
      const nextP = parts[i + 1];
      const pattern = getPattern(p, nextP);
      const key = Array.isArray(pattern) ? pattern[0] : p;
      if (key in curNode.#children) {
        curNode = curNode.#children[key];
        if (pattern) {
          possibleKeys.push(pattern[1]);
        }
        continue;
      }
      curNode.#children[key] = new _Node2();
      if (pattern) {
        curNode.#patterns.push(pattern);
        possibleKeys.push(pattern[1]);
      }
      curNode = curNode.#children[key];
    }
    curNode.#methods.push({
      [method]: {
        handler,
        possibleKeys: possibleKeys.filter((v, i, a) => a.indexOf(v) === i),
        score: this.#order
      }
    });
    return curNode;
  }
  #pushHandlerSets(handlerSets, node, method, nodeParams, params) {
    for (let i = 0, len = node.#methods.length; i < len; i++) {
      const m = node.#methods[i];
      const handlerSet = m[method] || m[METHOD_NAME_ALL];
      const processedSet = {};
      if (handlerSet !== void 0) {
        handlerSet.params = /* @__PURE__ */ Object.create(null);
        handlerSets.push(handlerSet);
        if (nodeParams !== emptyParams || params && params !== emptyParams) {
          for (let i2 = 0, len2 = handlerSet.possibleKeys.length; i2 < len2; i2++) {
            const key = handlerSet.possibleKeys[i2];
            const processed = processedSet[handlerSet.score];
            handlerSet.params[key] = params?.[key] && !processed ? params[key] : nodeParams[key] ?? params?.[key];
            processedSet[handlerSet.score] = true;
          }
        }
      }
    }
  }
  search(method, path) {
    const handlerSets = [];
    this.#params = emptyParams;
    const curNode = this;
    let curNodes = [curNode];
    const parts = splitPath(path);
    const curNodesQueue = [];
    const len = parts.length;
    let partOffsets = null;
    for (let i = 0; i < len; i++) {
      const part = parts[i];
      const isLast = i === len - 1;
      const tempNodes = [];
      for (let j = 0, len2 = curNodes.length; j < len2; j++) {
        const node = curNodes[j];
        const nextNode = node.#children[part];
        if (nextNode) {
          nextNode.#params = node.#params;
          if (isLast) {
            if (nextNode.#children["*"]) {
              this.#pushHandlerSets(handlerSets, nextNode.#children["*"], method, node.#params);
            }
            this.#pushHandlerSets(handlerSets, nextNode, method, node.#params);
          } else {
            tempNodes.push(nextNode);
          }
        }
        for (let k = 0, len3 = node.#patterns.length; k < len3; k++) {
          const pattern = node.#patterns[k];
          const params = node.#params === emptyParams ? {} : { ...node.#params };
          if (pattern === "*") {
            const astNode = node.#children["*"];
            if (astNode) {
              this.#pushHandlerSets(handlerSets, astNode, method, node.#params);
              astNode.#params = params;
              tempNodes.push(astNode);
            }
            continue;
          }
          const [key, name, matcher] = pattern;
          if (!part && !(matcher instanceof RegExp)) {
            continue;
          }
          const child = node.#children[key];
          if (matcher instanceof RegExp) {
            if (partOffsets === null) {
              partOffsets = new Array(len);
              let offset = path[0] === "/" ? 1 : 0;
              for (let p = 0; p < len; p++) {
                partOffsets[p] = offset;
                offset += parts[p].length + 1;
              }
            }
            const restPathString = path.substring(partOffsets[i]);
            const m = matcher.exec(restPathString);
            if (m) {
              params[name] = m[0];
              this.#pushHandlerSets(handlerSets, child, method, node.#params, params);
              if (hasChildren(child.#children)) {
                child.#params = params;
                const componentCount = m[0].match(/\//)?.length ?? 0;
                const targetCurNodes = curNodesQueue[componentCount] ||= [];
                targetCurNodes.push(child);
              }
              continue;
            }
          }
          if (matcher === true || matcher.test(part)) {
            params[name] = part;
            if (isLast) {
              this.#pushHandlerSets(handlerSets, child, method, params, node.#params);
              if (child.#children["*"]) {
                this.#pushHandlerSets(
                  handlerSets,
                  child.#children["*"],
                  method,
                  params,
                  node.#params
                );
              }
            } else {
              child.#params = params;
              tempNodes.push(child);
            }
          }
        }
      }
      const shifted = curNodesQueue.shift();
      curNodes = shifted ? tempNodes.concat(shifted) : tempNodes;
    }
    if (handlerSets.length > 1) {
      handlerSets.sort((a, b) => {
        return a.score - b.score;
      });
    }
    return [handlerSets.map(({ handler, params }) => [handler, params])];
  }
};

// ../../node_modules/.pnpm/hono@4.12.5/node_modules/hono/dist/router/trie-router/router.js
var TrieRouter = class {
  name = "TrieRouter";
  #node;
  constructor() {
    this.#node = new Node2();
  }
  add(method, path, handler) {
    const results = checkOptionalParameter(path);
    if (results) {
      for (let i = 0, len = results.length; i < len; i++) {
        this.#node.insert(method, results[i], handler);
      }
      return;
    }
    this.#node.insert(method, path, handler);
  }
  match(method, path) {
    return this.#node.search(method, path);
  }
};

// ../../node_modules/.pnpm/hono@4.12.5/node_modules/hono/dist/hono.js
var Hono2 = class extends Hono {
  /**
   * Creates an instance of the Hono class.
   *
   * @param options - Optional configuration options for the Hono instance.
   */
  constructor(options = {}) {
    super(options);
    this.router = options.router ?? new SmartRouter({
      routers: [new RegExpRouter(), new TrieRouter()]
    });
  }
};

// ../../node_modules/.pnpm/hono@4.12.5/node_modules/hono/dist/middleware/cors/index.js
var cors = (options) => {
  const defaults = {
    origin: "*",
    allowMethods: ["GET", "HEAD", "PUT", "POST", "DELETE", "PATCH"],
    allowHeaders: [],
    exposeHeaders: []
  };
  const opts = {
    ...defaults,
    ...options
  };
  const findAllowOrigin = ((optsOrigin) => {
    if (typeof optsOrigin === "string") {
      if (optsOrigin === "*") {
        return () => optsOrigin;
      } else {
        return (origin) => optsOrigin === origin ? origin : null;
      }
    } else if (typeof optsOrigin === "function") {
      return optsOrigin;
    } else {
      return (origin) => optsOrigin.includes(origin) ? origin : null;
    }
  })(opts.origin);
  const findAllowMethods = ((optsAllowMethods) => {
    if (typeof optsAllowMethods === "function") {
      return optsAllowMethods;
    } else if (Array.isArray(optsAllowMethods)) {
      return () => optsAllowMethods;
    } else {
      return () => [];
    }
  })(opts.allowMethods);
  return async function cors2(c, next) {
    function set(key, value) {
      c.res.headers.set(key, value);
    }
    const allowOrigin = await findAllowOrigin(c.req.header("origin") || "", c);
    if (allowOrigin) {
      set("Access-Control-Allow-Origin", allowOrigin);
    }
    if (opts.credentials) {
      set("Access-Control-Allow-Credentials", "true");
    }
    if (opts.exposeHeaders?.length) {
      set("Access-Control-Expose-Headers", opts.exposeHeaders.join(","));
    }
    if (c.req.method === "OPTIONS") {
      if (opts.origin !== "*") {
        set("Vary", "Origin");
      }
      if (opts.maxAge != null) {
        set("Access-Control-Max-Age", opts.maxAge.toString());
      }
      const allowMethods = await findAllowMethods(c.req.header("origin") || "", c);
      if (allowMethods.length) {
        set("Access-Control-Allow-Methods", allowMethods.join(","));
      }
      let headers = opts.allowHeaders;
      if (!headers?.length) {
        const requestHeaders = c.req.header("Access-Control-Request-Headers");
        if (requestHeaders) {
          headers = requestHeaders.split(/\s*,\s*/);
        }
      }
      if (headers?.length) {
        set("Access-Control-Allow-Headers", headers.join(","));
        c.res.headers.append("Vary", "Access-Control-Request-Headers");
      }
      c.res.headers.delete("Content-Length");
      c.res.headers.delete("Content-Type");
      return new Response(null, {
        headers: c.res.headers,
        status: 204,
        statusText: "No Content"
      });
    }
    await next();
    if (opts.origin !== "*") {
      c.header("Vary", "Origin", { append: true });
    }
  };
};

// src/index.ts
var import_path5 = require("path");

// src/lib/config.ts
var import_os = require("os");
var configuredBasePath = process.env.BASE_PATH || "/opc-monitor";
var fnnasDataRoot = process.env.TRIM_PKGHOME ? `${process.env.TRIM_PKGHOME}/data` : null;
var DATA_ROOT = process.env.OPENCLAW_DATA_DIR || fnnasDataRoot || "/tmp/openclaw-data";
var DEFAULT_INSTANCE_ID = process.env.OPENCLAW_DEFAULT_INSTANCE_ID || "default";
var MONITOR_BASE_PATH = configuredBasePath === "/" ? "" : `/${configuredBasePath}`.replace(/\/+/g, "/").replace(/\/$/, "");
var MONITOR_DB_DIR = `${DATA_ROOT}/monitor`;
var MONITOR_DB_PATH = `${MONITOR_DB_DIR}/monitor.sqlite`;
var SYSTEM_OPENCLAW_CONFIG_PATH = `${(0, import_os.homedir)()}/.openclaw/openclaw.json`;
var SYSTEM_OPENCLAW_LOG_PATH = `${(0, import_os.homedir)()}/.openclaw/logs/gateway.log`;
var SYSTEM_OPENCLAW_RUNTIME_LOG_DIR = `${(0, import_os.tmpdir)()}/openclaw`;
var MONITOR_ACCESS_MODE = process.env.MONITOR_ACCESS_MODE === "public" ? "public" : "lan";
var OPENCLAW_NPM_REGISTRY = process.env.OPENCLAW_NPM_REGISTRY || "https://registry.npmmirror.com/";
var SOUL_MD_SRC = process.env.SOUL_MD_SRC || null;
function normalizePublicBasePath(value) {
  if (!value || value === "/") {
    return "/";
  }
  const normalized = value.startsWith("/") ? value : `/${value}`;
  return normalized.endsWith("/") ? normalized : `${normalized}/`;
}
function buildInstanceProxyBasePath(instanceId) {
  const suffix = `/${instanceId}`;
  return MONITOR_BASE_PATH === "" ? suffix : `${MONITOR_BASE_PATH}${suffix}`;
}
function isLikelyDevEnvironment() {
  if (process.env.OPENCLAW_DEV_MODE === "1") {
    return true;
  }
  if (process.env.OPENCLAW_DEV_MODE === "0") {
    return false;
  }
  if (process.env.OPENCLAW_USE_SYSTEM_CONFIG === "1") {
    return true;
  }
  if (process.env.OPENCLAW_USE_SYSTEM_CONFIG === "0") {
    return false;
  }
  if (process.env.NODE_ENV === "production") {
    return false;
  }
  if (process.env.BUN_WATCH === "1") {
    return true;
  }
  const normalizedArgs = process.argv.map((arg) => arg.replace(/\\/g, "/"));
  return normalizedArgs.some(
    (arg) => arg === "--watch" || arg === "-w" || arg === "src/index.ts" || arg.endsWith("/src/index.ts")
  );
}

// src/lib/access-control.ts
function normalizeIp(value) {
  if (!value) {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  if (trimmed.startsWith("::ffff:")) {
    return trimmed.slice(7);
  }
  return trimmed;
}
function isLoopback(ip) {
  return ip === "127.0.0.1" || ip === "::1";
}
function isPrivateIpv4(ip) {
  const parts = ip.split(".").map((part) => Number(part));
  if (parts.length !== 4 || parts.some((part) => !Number.isInteger(part) || part < 0 || part > 255)) {
    return false;
  }
  const [first, second] = parts;
  if (first === 10) {
    return true;
  }
  if (first === 172 && second >= 16 && second <= 31) {
    return true;
  }
  if (first === 192 && second === 168) {
    return true;
  }
  if (first === 169 && second === 254) {
    return true;
  }
  return false;
}
function isPrivateIpv6(ip) {
  const lower = ip.toLowerCase();
  return lower.startsWith("fc") || lower.startsWith("fd") || lower.startsWith("fe8") || lower.startsWith("fe9") || lower.startsWith("fea") || lower.startsWith("feb");
}
function isLanClientIp(ip) {
  const normalized = normalizeIp(ip);
  if (!normalized) {
    return false;
  }
  if (isLoopback(normalized)) {
    return true;
  }
  if (normalized.includes(".")) {
    return isPrivateIpv4(normalized);
  }
  if (normalized.includes(":")) {
    return isPrivateIpv6(normalized);
  }
  return false;
}
function shouldAllowClientIp(ip) {
  if (MONITOR_ACCESS_MODE === "public") {
    return true;
  }
  return isLanClientIp(ip);
}
function accessDeniedResponse(ip) {
  const message = {
    message: "Access denied: monitor is restricted to LAN and localhost clients.",
    clientIp: normalizeIp(ip),
    accessMode: MONITOR_ACCESS_MODE
  };
  return Response.json(message, { status: 403 });
}

// src/lib/auth/config.ts
function envFlag(name) {
  const value = process.env[name];
  if (value === "1" || value?.toLowerCase() === "true") {
    return true;
  }
  if (value === "0" || value?.toLowerCase() === "false") {
    return false;
  }
  return null;
}
function envNumber(name, fallback, min, max) {
  const raw2 = process.env[name];
  if (raw2 === void 0 || raw2 === "") {
    return fallback;
  }
  const value = Number(raw2);
  if (!Number.isFinite(value) || value < min || value > max) {
    console.warn(`[auth:config] invalid ${name}="${raw2}", using default ${fallback} (range ${min}-${max})`);
    return fallback;
  }
  return value;
}
function envString(name) {
  const value = process.env[name];
  if (typeof value !== "string") {
    return void 0;
  }
  const trimmed = value.trim();
  return trimmed === "" ? void 0 : trimmed;
}
function normalizeBypassPath(path) {
  if (!path) {
    return "/";
  }
  return path.startsWith("/") ? path : `/${path}`;
}
var defaultHealthPath = `${MONITOR_BASE_PATH || ""}/api/health` || "/api/health";
var configuredBypassPaths = process.env.FN_AUTH_BYPASS_PATHS ? process.env.FN_AUTH_BYPASS_PATHS.split(",").map((part) => normalizeBypassPath(part.trim())).filter(Boolean) : [defaultHealthPath];
var FN_AUTH_ENABLED = envFlag("FN_AUTH_ENABLED") ?? !isLikelyDevEnvironment();
var FN_AUTH_FNOS_COOKIE_NAME = envString("FN_AUTH_FNOS_COOKIE_NAME") ?? envString("FN_AUTH_COOKIE_NAME") ?? "fnos-token";
var FN_AUTH_COOKIE_NAME = FN_AUTH_FNOS_COOKIE_NAME;
var FN_AUTH_ENTRY_COOKIE_NAME = envString("FN_AUTH_ENTRY_COOKIE_NAME") ?? "entry-token";
var FN_AUTH_TIMEOUT_MS = envNumber("FN_AUTH_TIMEOUT_MS", 2e3, 100, 3e4);
var FN_AUTH_CACHE_TTL_MS = envNumber("FN_AUTH_CACHE_TTL_MS", 12e4, 0, 6e5);
var FN_AUTH_ENTRY_TIMEOUT_MS = envNumber(
  "FN_AUTH_ENTRY_TIMEOUT_MS",
  FN_AUTH_TIMEOUT_MS,
  100,
  3e4
);
var FN_AUTH_ENTRY_CACHE_TTL_MS = envNumber(
  "FN_AUTH_ENTRY_CACHE_TTL_MS",
  FN_AUTH_CACHE_TTL_MS,
  0,
  6e5
);
var FN_AUTH_ENTRY_ENDPOINT = envString("FN_AUTH_ENTRY_ENDPOINT");
var FN_AUTH_MACHINE_ID = envString("FN_AUTH_MACHINE_ID");
var FN_AUTH_MODE = envString("FN_AUTH_MODE") ?? "sac";
var FN_AUTH_SAC_ENDPOINT = envString("FN_AUTH_SAC_ENDPOINT");
var FN_AUTH_DEVICE_ID_PATH = envString("FN_AUTH_DEVICE_ID_PATH");
var FN_AUTH_REQUIRE_SAME_ORIGIN = envFlag("FN_AUTH_REQUIRE_SAME_ORIGIN") ?? (FN_AUTH_ENABLED && !isLikelyDevEnvironment());
var FN_AUTH_BYPASS_PATHS = configuredBypassPaths;
function isAuthBypassedPath(pathname, method) {
  if (method !== "GET" && method !== "HEAD") {
    return false;
  }
  return FN_AUTH_BYPASS_PATHS.includes(pathname);
}

// src/lib/auth/cookies.ts
var MAX_COOKIE_VALUE_LENGTH = 4096;
function parseCookieHeader(header) {
  const cookies = /* @__PURE__ */ new Map();
  if (!header) {
    return cookies;
  }
  for (const part of header.split(";")) {
    const trimmed = part.trim();
    if (!trimmed) {
      continue;
    }
    const separator = trimmed.indexOf("=");
    if (separator <= 0) {
      continue;
    }
    const name = trimmed.slice(0, separator).trim();
    const value = trimmed.slice(separator + 1).trim();
    if (!name || value.length > MAX_COOKIE_VALUE_LENGTH) {
      continue;
    }
    try {
      cookies.set(name, decodeURIComponent(value));
    } catch {
    }
  }
  return cookies;
}
function getCookieValue(request, name) {
  const cookies = parseCookieHeader(request.headers.get("cookie"));
  const value = cookies.get(name);
  return typeof value === "string" && value.length > 0 ? value : null;
}

// ../../packages/fn-token-auth/src/core/constants.js
var TRIM_HEADER_MAGIC = 1414680643;
var RPC_PACKET_HEADER_SIZE = 30;
var TRIMSRV_PACKET_HEADER_SIZE = 12;
var CURRENT_REVISION = 1;
var SERVICE_TYPE = {
  TRIMAPP: 0,
  TRIMSRV: 1
};
var BROKER_SERVICE_ID = "com.trim.rpcbroker";
var BROKER_METHOD_APPLY = "apply";
var DEFAULT_BROKER_ENDPOINT = "/run/trim_app_cgi/rpcbroker";
var TRIMSRV_COMMAND = {
  TOKEN_QUERY: 2
};
var TRIMSRV_STATUS = {
  SUCCESS: 0,
  INVALID_TOKEN: 135168,
  NOT_SUPPORT: 100000004
};

// ../../packages/fn-token-auth/src/core/errors.js
var FnTokenAuthError = class extends Error {
  constructor(message, options = {}) {
    super(message, options.cause ? { cause: options.cause } : void 0);
    this.name = this.constructor.name;
    if (options.code) {
      this.code = options.code;
    }
    if (options.details !== void 0) {
      this.details = options.details;
    }
  }
};
var ConfigurationError = class extends FnTokenAuthError {
};
var TokenFormatError = class extends FnTokenAuthError {
};
var PermissionApplyError = class extends FnTokenAuthError {
};
var ServiceDiscoveryError = class extends FnTokenAuthError {
};
var TransportConnectError = class extends FnTokenAuthError {
};
var TransportTimeoutError = class extends FnTokenAuthError {
};
var RpcProtocolError = class extends FnTokenAuthError {
};
var InvalidFnOsTokenError = class extends FnTokenAuthError {
};
var FnOsAuthBackendError = class extends FnTokenAuthError {
};
var EntryTokenValidationError = class extends FnTokenAuthError {
};

// ../../packages/fn-token-auth/src/core/utils.js
var import_node_crypto = __toESM(require("node:crypto"), 1);
function generateReqId() {
  return import_node_crypto.default.randomBytes(8).toString("hex");
}
function getCurrentUid() {
  if (typeof process.getuid === "function") {
    return process.getuid() >>> 0;
  }
  return 0;
}
function normalizeServiceType(value) {
  if (value === 1 || value === "1" || value === "TRIMSRV") {
    return "TRIMSRV";
  }
  return "TRIMAPP";
}
function trimNullTerminatedString(buffer) {
  let end = buffer.length;
  while (end > 0 && buffer[end - 1] === 0) {
    end -= 1;
  }
  return buffer.subarray(0, end).toString("utf8");
}
function createSessionSeed() {
  return BigInt(Date.now()) * 1000n;
}
function toConnectionOptions(endpoint) {
  if (typeof endpoint !== "string") {
    return endpoint;
  }
  if (endpoint.startsWith("tcp://")) {
    const url = new URL(endpoint);
    return {
      host: url.hostname,
      port: Number(url.port)
    };
  }
  return endpoint;
}

// ../../packages/fn-token-auth/src/core/packet/rpc-packet.js
var DATA_KEY_BEGIN = '{"data":';
var DATA_KEY_END = "}";
function encodeRpcRequestPacket({
  sessionId,
  appId,
  appKey,
  requestName,
  payload
}) {
  const inner = {
    req: requestName,
    reqid: generateReqId(),
    ...payload ?? {}
  };
  const bodyJson = `${DATA_KEY_BEGIN}${JSON.stringify(inner)}${DATA_KEY_END}`;
  const bodyBytes = Buffer.from(bodyJson, "utf8");
  const appIdBytes = Buffer.from(appId, "utf8");
  const appKeyBytes = Buffer.from(appKey, "utf8");
  const header = Buffer.alloc(RPC_PACKET_HEADER_SIZE);
  header.writeUInt32LE(TRIM_HEADER_MAGIC, 0);
  header.writeUInt16LE(CURRENT_REVISION, 4);
  header.writeBigUInt64LE(sessionId, 6);
  header.writeUInt16LE(appIdBytes.length, 14);
  header.writeUInt16LE(appKeyBytes.length, 16);
  header.writeUInt32LE(bodyBytes.length, 18);
  header.writeUInt32LE(getCurrentUid(), 22);
  header.writeUInt32LE(0, 26);
  return {
    reqid: inner.reqid,
    buffer: Buffer.concat([header, appIdBytes, appKeyBytes, bodyBytes])
  };
}
function decodeRpcResponseFrame(frame) {
  if (frame.header.length !== RPC_PACKET_HEADER_SIZE) {
    throw new RpcProtocolError("Invalid RPC header length");
  }
  const magic = frame.header.readUInt32LE(0);
  if (magic !== TRIM_HEADER_MAGIC) {
    throw new RpcProtocolError(`Unexpected RPC magic: ${magic}`);
  }
  const appIdLength = frame.header.readUInt16LE(14);
  const appKeyLength = frame.header.readUInt16LE(16);
  const dataLength = frame.header.readUInt32LE(18);
  const extraDataLength = frame.header.readUInt32LE(26);
  const expectedLength = appIdLength + appKeyLength + dataLength + extraDataLength;
  if (frame.body.length !== expectedLength) {
    throw new RpcProtocolError("RPC body length does not match header");
  }
  const innerJsonStart = appIdLength + appKeyLength;
  const innerJson = frame.body.subarray(innerJsonStart, innerJsonStart + dataLength).toString("utf8");
  if (!innerJson.startsWith(DATA_KEY_BEGIN) || !innerJson.endsWith(DATA_KEY_END)) {
    throw new RpcProtocolError("RPC payload wrapper is invalid");
  }
  const innerData = innerJson.slice(DATA_KEY_BEGIN.length, -DATA_KEY_END.length);
  const parsed = JSON.parse(innerData);
  return {
    sessionId: frame.sessionId,
    result: parsed.result ?? "",
    reqid: parsed.reqid ?? "",
    errno: parsed.errno ?? 0,
    errmsg: parsed.errmsg ?? "",
    data: parsed.data
  };
}

// ../../packages/fn-token-auth/src/core/broker-client.js
var BrokerClient = class {
  #appId;
  #appKey;
  #timeoutMs;
  #sessionFactory;
  #transportPool;
  #endpoint;
  constructor({ appId, appKey, timeoutMs, sessionFactory, transportPool, endpoint = DEFAULT_BROKER_ENDPOINT }) {
    this.#appId = appId;
    this.#appKey = appKey;
    this.#timeoutMs = timeoutMs;
    this.#sessionFactory = sessionFactory;
    this.#transportPool = transportPool;
    this.#endpoint = endpoint;
  }
  async apply(serviceIds) {
    const sessionId = this.#sessionFactory.nextRpcSessionId();
    const transport = this.#transportPool.getOrCreate(this.#endpoint, "rpc");
    const { buffer } = encodeRpcRequestPacket({
      sessionId,
      appId: this.#appId,
      appKey: this.#appKey,
      requestName: `${BROKER_SERVICE_ID}.${BROKER_METHOD_APPLY}`,
      payload: {
        pid: process.pid,
        services: serviceIds
      }
    });
    const frame = await transport.request(sessionId, buffer, this.#timeoutMs);
    const response = decodeRpcResponseFrame(frame);
    if (response.result !== "succ") {
      throw new PermissionApplyError("Broker apply permission failed", {
        code: response.errno,
        details: response
      });
    }
    if (!Array.isArray(response.data)) {
      throw new ServiceDiscoveryError("Broker did not return a service array", {
        details: response
      });
    }
    const descriptors = response.data.map((service) => ({
      id: service.id,
      name: service.name,
      endpoint: service.uds,
      ip: service.ip,
      token: service.token,
      type: normalizeServiceType(service.type === SERVICE_TYPE.TRIMSRV ? "TRIMSRV" : service.type)
    }));
    if (descriptors.length < serviceIds.length) {
      throw new ServiceDiscoveryError("Broker returned fewer services than requested", {
        details: { requested: serviceIds, received: descriptors }
      });
    }
    return descriptors;
  }
};

// ../../packages/fn-token-auth/src/core/service-registry.js
var ServiceRegistry = class {
  #brokerClient;
  #services = /* @__PURE__ */ new Map();
  constructor({ brokerClient }) {
    this.#brokerClient = brokerClient;
  }
  async ensure(serviceIds) {
    const missing = serviceIds.filter((serviceId) => !this.#services.has(serviceId));
    if (missing.length === 0) {
      return;
    }
    const descriptors = await this.#brokerClient.apply(missing);
    for (const descriptor of descriptors) {
      this.#services.set(descriptor.id, descriptor);
    }
  }
  get(serviceId) {
    const descriptor = this.#services.get(serviceId);
    if (!descriptor) {
      throw new ServiceDiscoveryError(`Service not found in registry: ${serviceId}`);
    }
    return descriptor;
  }
};

// ../../packages/fn-token-auth/src/core/packet/trimsrv-packet.js
function encodeTrimSrvTokenQueryPacket({ sessionId, token }) {
  if (!token) {
    throw new TokenFormatError("fnos token is required");
  }
  let tokenBytes;
  try {
    tokenBytes = Buffer.from(token, "base64");
  } catch (error) {
    throw new TokenFormatError("fnos token is not valid base64", { cause: error });
  }
  if (tokenBytes.length === 0 || tokenBytes.toString("base64") !== normalizeBase64(token)) {
    throw new TokenFormatError("fnos token is not valid standard base64");
  }
  const packetLength = 16 + tokenBytes.length;
  const header = Buffer.alloc(16);
  header.writeUInt32LE(packetLength, 0);
  header.writeUInt32LE(TRIMSRV_COMMAND.TOKEN_QUERY, 4);
  header.writeBigUInt64LE(sessionId, 8);
  return Buffer.concat([header, tokenBytes]);
}
function decodeTrimSrvTokenQueryResponse(frame) {
  if (frame.header.length !== TRIMSRV_PACKET_HEADER_SIZE) {
    throw new RpcProtocolError("Invalid TRIMSRV header length");
  }
  if (frame.body.length < 12) {
    throw new RpcProtocolError("TRIMSRV tokenQuery response body is too short");
  }
  const uid = frame.body.readUInt32LE(0);
  const isAdminRaw = frame.body.readBigUInt64LE(4);
  const userName = trimNullTerminatedString(frame.body.subarray(12));
  if (uid === 4294967295) {
    throw new InvalidFnOsTokenError("fnos token is invalid", {
      code: TRIMSRV_STATUS.INVALID_TOKEN,
      details: {
        isAdminRaw,
        userName
      }
    });
  }
  return {
    uid,
    userName,
    isAdminRaw,
    isAdmin: isAdminRaw !== 0n
  };
}
function decodeTrimSrvFrameHeader(header) {
  if (header.length !== TRIMSRV_PACKET_HEADER_SIZE) {
    throw new RpcProtocolError("Invalid TRIMSRV header length");
  }
  return {
    packetLength: header.readUInt32LE(0),
    sessionId: header.readBigUInt64LE(4)
  };
}
function composeTrimSrvSessionId(seed, commandId) {
  return (seed & 0xffffffffn) << 32n | BigInt(commandId >>> 0);
}
function normalizeBase64(input) {
  return input.replace(/\s+/g, "");
}

// ../../packages/fn-token-auth/src/core/session-factory.js
var SessionFactory = class {
  #current = createSessionSeed();
  nextRpcSessionId() {
    this.#current += 1n;
    return this.#current;
  }
  nextTrimSrvSessionId(commandId = TRIMSRV_COMMAND.TOKEN_QUERY) {
    this.#current += 1n;
    return composeTrimSrvSessionId(this.#current, commandId);
  }
};

// ../../packages/fn-token-auth/src/core/ipc-transport.js
var import_node_net = __toESM(require("node:net"), 1);
var IpcTransport = class {
  #endpoint;
  #protocol;
  #socket = null;
  #connected = false;
  #connectPromise = null;
  #pending = /* @__PURE__ */ new Map();
  #buffer = Buffer.alloc(0);
  #closed = false;
  constructor({ endpoint, protocol }) {
    this.#endpoint = endpoint;
    this.#protocol = protocol;
  }
  async request(sessionId, payload, timeoutMs) {
    await this.#connect();
    return new Promise((resolve2, reject) => {
      const timeout = setTimeout(() => {
        this.#pending.delete(sessionId.toString());
        reject(new TransportTimeoutError(`IPC request timed out after ${timeoutMs}ms`, {
          details: { endpoint: this.#endpoint, sessionId: sessionId.toString() }
        }));
      }, timeoutMs);
      this.#pending.set(sessionId.toString(), {
        resolve(frame) {
          clearTimeout(timeout);
          resolve2(frame);
        },
        reject(error) {
          clearTimeout(timeout);
          reject(error);
        }
      });
      this.#socket.write(payload, (error) => {
        if (error) {
          const pending = this.#pending.get(sessionId.toString());
          if (pending) {
            this.#pending.delete(sessionId.toString());
            pending.reject(new TransportConnectError("IPC write failed", {
              cause: error,
              details: { endpoint: this.#endpoint, sessionId: sessionId.toString() }
            }));
          }
        }
      });
    });
  }
  async close() {
    this.#closed = true;
    if (!this.#socket) {
      return;
    }
    this.#socket.destroy();
    this.#socket = null;
    this.#connected = false;
  }
  async #connect() {
    if (this.#closed) {
      throw new TransportConnectError("IPC transport is already closed");
    }
    if (this.#connected && this.#socket) {
      return;
    }
    if (this.#connectPromise) {
      return this.#connectPromise;
    }
    this.#connectPromise = new Promise((resolve2, reject) => {
      const socket = import_node_net.default.createConnection(toConnectionOptions(this.#endpoint));
      const onError = (error) => {
        socket.removeAllListeners();
        this.#connectPromise = null;
        reject(new TransportConnectError(`Failed to connect to IPC endpoint ${this.#endpoint}`, {
          cause: error,
          details: { endpoint: this.#endpoint }
        }));
      };
      socket.once("error", onError);
      socket.once("connect", () => {
        socket.removeListener("error", onError);
        this.#socket = socket;
        this.#connected = true;
        this.#connectPromise = null;
        socket.on("data", (chunk) => {
          this.#buffer = Buffer.concat([this.#buffer, chunk]);
          this.#drainFrames();
        });
        socket.on("close", () => {
          this.#connected = false;
          this.#socket = null;
          this.#failPending(new TransportConnectError(`IPC endpoint closed: ${this.#endpoint}`));
        });
        socket.on("error", (error) => {
          this.#connected = false;
          this.#socket = null;
          this.#failPending(new TransportConnectError(`IPC endpoint error: ${this.#endpoint}`, {
            cause: error
          }));
        });
        resolve2();
      });
    });
    return this.#connectPromise;
  }
  #drainFrames() {
    while (true) {
      const headerLength = this.#protocol === "rpc" ? RPC_PACKET_HEADER_SIZE : TRIMSRV_PACKET_HEADER_SIZE;
      if (this.#buffer.length < headerLength) {
        return;
      }
      const header = this.#buffer.subarray(0, headerLength);
      const frame = this.#protocol === "rpc" ? parseRpcFrameHeader(header) : parseTrimSrvFrameHeader(header);
      const totalLength = headerLength + frame.bodyLength;
      if (this.#buffer.length < totalLength) {
        return;
      }
      const body = this.#buffer.subarray(headerLength, totalLength);
      this.#buffer = this.#buffer.subarray(totalLength);
      const pending = this.#pending.get(frame.sessionId.toString());
      if (!pending) {
        continue;
      }
      this.#pending.delete(frame.sessionId.toString());
      pending.resolve({
        sessionId: frame.sessionId,
        header,
        body
      });
    }
  }
  #failPending(error) {
    for (const [key, pending] of this.#pending.entries()) {
      this.#pending.delete(key);
      pending.reject(error);
    }
  }
};
function parseRpcFrameHeader(header) {
  const appIdLength = header.readUInt16LE(14);
  const appKeyLength = header.readUInt16LE(16);
  const dataLength = header.readUInt32LE(18);
  const extraDataLength = header.readUInt32LE(26);
  return {
    sessionId: header.readBigUInt64LE(6),
    bodyLength: appIdLength + appKeyLength + dataLength + extraDataLength
  };
}
function parseTrimSrvFrameHeader(header) {
  const packetLength = header.readUInt32LE(0);
  return {
    sessionId: header.readBigUInt64LE(4),
    bodyLength: packetLength - TRIMSRV_PACKET_HEADER_SIZE
  };
}

// ../../packages/fn-token-auth/src/core/transport-pool.js
var TransportPool = class {
  #transports = /* @__PURE__ */ new Map();
  getOrCreate(endpoint, protocol) {
    const key = `${protocol}:${endpoint}`;
    if (!this.#transports.has(key)) {
      this.#transports.set(key, new IpcTransport({ endpoint, protocol }));
    }
    return this.#transports.get(key);
  }
  async closeAll() {
    const transports = [...this.#transports.values()];
    this.#transports.clear();
    await Promise.all(transports.map((transport) => transport.close()));
  }
};

// ../../packages/fn-token-auth/src/providers/entry/sac-entry-provider.js
var SacEntryTokenProvider = class {
  #entryClient;
  constructor({ entryClient }) {
    this.#entryClient = entryClient;
  }
  async verify(token, context) {
    const detailed = await this.#entryClient.validateTokenDetailed({
      token,
      machineId: context.machineId,
      timeoutMs: context.timeoutMs
    });
    return {
      valid: detailed.ok,
      details: detailed
    };
  }
};

// ../../packages/fn-token-auth/src/services/trimapp-client.js
var TrimAppClient = class {
  #appId;
  #appKey;
  #timeoutMs;
  #sessionFactory;
  #transportPool;
  #serviceRegistry;
  constructor({ appId, appKey, timeoutMs, sessionFactory, transportPool, serviceRegistry }) {
    this.#appId = appId;
    this.#appKey = appKey;
    this.#timeoutMs = timeoutMs;
    this.#sessionFactory = sessionFactory;
    this.#transportPool = transportPool;
    this.#serviceRegistry = serviceRegistry;
  }
  async call(serviceId, method, payload) {
    await this.#serviceRegistry.ensure([serviceId]);
    const descriptor = this.#serviceRegistry.get(serviceId);
    const sessionId = this.#sessionFactory.nextRpcSessionId();
    const transport = this.#transportPool.getOrCreate(descriptor.endpoint, "rpc");
    const { buffer } = encodeRpcRequestPacket({
      sessionId,
      appId: this.#appId,
      appKey: this.#appKey,
      requestName: `${serviceId}.${method}`,
      payload
    });
    const frame = await transport.request(sessionId, buffer, this.#timeoutMs);
    const response = decodeRpcResponseFrame(frame);
    if (response.result !== "succ") {
      throw new RpcProtocolError(`TRIMAPP call failed: ${serviceId}.${method}`, {
        code: response.errno,
        details: response
      });
    }
    return response.data;
  }
};

// ../../packages/fn-token-auth/src/services/sac-entry-client.js
var import_node_crypto2 = __toESM(require("node:crypto"), 1);

// ../../packages/fn-token-auth/src/core/http-transport.js
var import_node_http = __toESM(require("node:http"), 1);
var import_node_url = require("node:url");
async function httpRequest({
  endpoint,
  path,
  method = "GET",
  headers = {},
  body = null,
  timeoutMs = 5e3
}) {
  const isUnixSocket = endpoint.startsWith("/");
  const isTcp = endpoint.startsWith("tcp://");
  const options = isUnixSocket ? buildUnixSocketOptions(endpoint, path, method, headers) : isTcp ? buildTcpOptions(endpoint, path, method, headers) : buildHttpOptions(endpoint, path, method, headers);
  return new Promise((resolve2, reject) => {
    let timedOut = false;
    const request = import_node_http.default.request(options, (response) => {
      const chunks = [];
      response.on("data", (chunk) => {
        chunks.push(chunk);
      });
      response.on("end", () => {
        clearTimeout(timer);
        resolve2({
          statusCode: response.statusCode ?? 0,
          bodyText: Buffer.concat(chunks).toString("utf8")
        });
      });
      response.on("error", (error) => {
        clearTimeout(timer);
        reject(
          new TransportConnectError("HTTP response read failed", {
            cause: error,
            details: { endpoint, path, method }
          })
        );
      });
    });
    const timer = setTimeout(() => {
      timedOut = true;
      request.destroy(new Error("timeout"));
    }, timeoutMs);
    request.on("error", (error) => {
      clearTimeout(timer);
      if (timedOut) {
        reject(
          new TransportTimeoutError(`HTTP request timed out after ${timeoutMs}ms`, {
            cause: error,
            details: { endpoint, path, method }
          })
        );
        return;
      }
      reject(
        new TransportConnectError("HTTP request failed", {
          cause: error,
          details: { endpoint, path, method }
        })
      );
    });
    if (body) {
      request.write(body);
    }
    request.end();
  });
}
function buildUnixSocketOptions(socketPath, path, method, headers) {
  return {
    socketPath,
    path,
    method,
    headers: {
      Host: "unix",
      ...headers
    }
  };
}
function buildTcpOptions(tcpUrl, path, method, headers) {
  const url = new import_node_url.URL(tcpUrl);
  return {
    hostname: url.hostname,
    port: Number(url.port),
    path,
    method,
    headers: {
      Host: `${url.hostname}:${url.port}`,
      ...headers
    }
  };
}
function buildHttpOptions(baseUrl, path, method, headers) {
  const url = new import_node_url.URL(path, baseUrl);
  return {
    hostname: url.hostname,
    port: url.port || (url.protocol === "https:" ? 443 : 80),
    path: url.pathname + url.search,
    method,
    headers: {
      Host: url.host,
      ...headers
    }
  };
}

// ../../packages/fn-token-auth/src/services/sac-entry-client.js
var DEFAULT_ENTRY_ENDPOINT = "/var/run/trim_sac.socket";
var DEFAULT_ENTRY_PATH = "/sac/entry/v1/token/validate";
var SAC_API_KEY = "trim.sac";
var DEFAULT_TIMEOUT_MS = 2e3;
var SacEntryClient = class {
  #endpoint;
  #timeoutMs;
  constructor({ endpoint = DEFAULT_ENTRY_ENDPOINT, timeoutMs = DEFAULT_TIMEOUT_MS } = {}) {
    this.#endpoint = endpoint;
    this.#timeoutMs = timeoutMs;
  }
  async validateTokenDetailed({ token, machineId, timeoutMs = this.#timeoutMs }) {
    const normalizedToken = requireNonEmptyString(token, "entry token is required");
    const normalizedMachineId = requireNonEmptyString(machineId, "machineId is required");
    const requestBody = JSON.stringify({
      token: normalizedToken
    });
    const timestampMs = Date.now().toString();
    const sign = createSacSign({
      apiKey: SAC_API_KEY,
      timestampMs,
      machineId: normalizedMachineId
    });
    const { statusCode, bodyText } = await httpRequest({
      endpoint: this.#endpoint,
      path: DEFAULT_ENTRY_PATH,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Sac-Ts": timestampMs,
        "Sac-Sign": sign
      },
      body: requestBody,
      timeoutMs
    });
    return parseEntryResponse(statusCode, bodyText);
  }
};
function parseEntryResponse(statusCode, bodyText) {
  if (bodyText === void 0 || bodyText === null) {
    throw new EntryTokenValidationError(
      `Empty response from entry validation (HTTP ${statusCode})`,
      { details: { statusCode } }
    );
  }
  let parsed;
  try {
    parsed = JSON.parse(bodyText);
  } catch {
    throw new EntryTokenValidationError(
      `Invalid JSON response from entry validation: ${bodyText.slice(0, 200)}`,
      { details: { statusCode, bodyText: bodyText.slice(0, 200) } }
    );
  }
  if (parsed.code !== 0) {
    throw new EntryTokenValidationError(
      `Entry validation service error: code=${parsed.code}, msg=${parsed.msg ?? ""}`,
      { details: { code: parsed.code, msg: parsed.msg } }
    );
  }
  return {
    ok: !!parsed.data?.valid,
    status: parsed.data?.valid ? "valid" : "invalid",
    raw: parsed
  };
}
function createSacSign({ apiKey = SAC_API_KEY, timestampMs, machineId }) {
  return import_node_crypto2.default.createHash("md5").update(`${apiKey}\`${timestampMs}\`${machineId}`).digest("hex");
}
function requireNonEmptyString(value, message) {
  if (typeof value !== "string" || value.trim() === "") {
    throw new TokenFormatError(message);
  }
  return value.trim();
}

// ../../packages/fn-token-auth/src/services/trim-main-client.js
var TrimMainClient = class {
  #timeoutMs;
  #sessionFactory;
  #transportPool;
  #serviceRegistry;
  constructor({ timeoutMs, sessionFactory, transportPool, serviceRegistry }) {
    this.#timeoutMs = timeoutMs;
    this.#sessionFactory = sessionFactory;
    this.#transportPool = transportPool;
    this.#serviceRegistry = serviceRegistry;
  }
  async tokenQuery(token) {
    const detailed = await this.tokenQueryDetailed(token);
    if (!detailed.ok) {
      throw detailed.error;
    }
    return detailed.identity;
  }
  async tokenQueryDetailed(token) {
    const serviceId = "com.trim.main";
    const method = "tokenQuery";
    await this.#serviceRegistry.ensure([serviceId]);
    const descriptor = this.#serviceRegistry.get(serviceId);
    const sessionId = this.#sessionFactory.nextTrimSrvSessionId(TRIMSRV_COMMAND.TOKEN_QUERY);
    const transport = this.#transportPool.getOrCreate(descriptor.endpoint, "trimsrv");
    const payload = encodeTrimSrvTokenQueryPacket({ sessionId, token });
    const frame = await transport.request(sessionId, payload, this.#timeoutMs);
    const requestSummary = {
      serviceId,
      method,
      endpoint: descriptor.endpoint,
      sessionId: sessionId.toString(),
      commandId: TRIMSRV_COMMAND.TOKEN_QUERY,
      packetLength: payload.length,
      tokenBase64: token,
      tokenBytesHex: payload.subarray(16).toString("hex")
    };
    const responseHeader = decodeTrimSrvFrameHeader(frame.header);
    const responseSummary = {
      packetLength: responseHeader.packetLength,
      sessionId: responseHeader.sessionId.toString(),
      bodyLength: frame.body.length,
      bodyHex: frame.body.toString("hex")
    };
    try {
      const identity = decodeTrimSrvTokenQueryResponse(frame);
      return {
        ok: true,
        status: "valid",
        request: requestSummary,
        response: responseSummary,
        identity
      };
    } catch (error) {
      if (error instanceof InvalidFnOsTokenError) {
        return {
          ok: false,
          status: "invalid",
          request: requestSummary,
          response: responseSummary,
          error: serializeError(error)
        };
      }
      throw error;
    }
  }
};
function serializeError(error) {
  return {
    name: error.name,
    message: error.message,
    code: error.code,
    details: error.details
  };
}

// ../../packages/fn-token-auth/src/services/trim-sysinfo-client.js
var TrimSysinfoClient = class {
  #trimAppClient;
  constructor({ trimAppClient }) {
    this.#trimAppClient = trimAppClient;
  }
  async getMachineId() {
    const data = await this.#trimAppClient.call("com.trim.sysinfo", "getMachineId", null);
    return data?.machineId ?? "";
  }
};

// ../../packages/fn-token-auth/src/core/cache.js
var ExpiringCache = class {
  #store = /* @__PURE__ */ new Map();
  #maxEntries;
  #cleanupInterval;
  #writesSinceCleanup = 0;
  constructor({ maxEntries = 4096, cleanupInterval = 128 } = {}) {
    this.#maxEntries = Number.isFinite(maxEntries) && maxEntries > 0 ? Math.floor(maxEntries) : 0;
    this.#cleanupInterval = Number.isFinite(cleanupInterval) && cleanupInterval > 0 ? Math.floor(cleanupInterval) : 1;
  }
  get(key) {
    const item = this.#store.get(key);
    if (!item) {
      return void 0;
    }
    if (item.expiresAt <= Date.now()) {
      this.#store.delete(key);
      return void 0;
    }
    return item.value;
  }
  set(key, value, ttlMs) {
    if (this.#maxEntries === 0) {
      return;
    }
    if (this.#store.has(key)) {
      this.#store.delete(key);
    }
    this.#store.set(key, {
      value,
      expiresAt: Date.now() + ttlMs
    });
    this.#writesSinceCleanup += 1;
    if (this.#writesSinceCleanup >= this.#cleanupInterval) {
      this.#writesSinceCleanup = 0;
      this.#pruneExpired();
    }
    while (this.#store.size > this.#maxEntries) {
      this.#pruneExpired();
      if (this.#store.size <= this.#maxEntries) {
        break;
      }
      const oldestKey = this.#store.keys().next().value;
      if (oldestKey === void 0) {
        break;
      }
      this.#store.delete(oldestKey);
    }
  }
  clear() {
    this.#store.clear();
  }
  #pruneExpired() {
    const now = Date.now();
    for (const [key, item] of this.#store.entries()) {
      if (item.expiresAt <= now) {
        this.#store.delete(key);
      }
    }
  }
};
var InflightDeduper = class {
  #store = /* @__PURE__ */ new Map();
  run(key, factory) {
    if (this.#store.has(key)) {
      return this.#store.get(key);
    }
    const promise = Promise.resolve().then(factory).finally(() => {
      this.#store.delete(key);
    });
    this.#store.set(key, promise);
    return promise;
  }
};

// ../../packages/fn-token-auth/src/validators/entry-validator.js
var EntryTokenValidator = class {
  #entryProvider;
  #cache;
  #deduper;
  #enableCache;
  #cacheTtlMs;
  #defaultTimeoutMs;
  #machineId;
  #machineIdResolver;
  #machineIdPromise = null;
  constructor({
    entryProvider,
    machineId,
    machineIdResolver,
    enableCache = true,
    cacheTtlMs,
    defaultTimeoutMs
  }) {
    this.#entryProvider = entryProvider;
    this.#cache = new ExpiringCache();
    this.#deduper = new InflightDeduper();
    this.#enableCache = enableCache;
    this.#cacheTtlMs = cacheTtlMs;
    this.#defaultTimeoutMs = defaultTimeoutMs;
    this.#machineId = normalizeOptionalString(machineId);
    this.#machineIdResolver = machineIdResolver;
  }
  async verify(token, options = {}) {
    const result = await this.verifyDetailed(token, options);
    if (result.status === "error") {
      throw result.error;
    }
    return result.ok;
  }
  async verifyDetailed(token, options = {}) {
    try {
      const normalizedToken = requireNonEmptyToken(token);
      const machineId = await this.#resolveMachineId(options.machineId);
      const timeoutMs = options.timeoutMs ?? this.#defaultTimeoutMs;
      const cacheKey2 = `${machineId}:${normalizedToken}`;
      if (this.#enableCache) {
        const cached = this.#cache.get(cacheKey2);
        if (cached) {
          return {
            ok: true,
            status: "valid",
            machineId,
            cached: true
          };
        }
        return this.#deduper.run(cacheKey2, async () => {
          const result = await this.#callProvider(normalizedToken, { machineId, timeoutMs });
          if (result.ok && result.cacheable !== false) {
            this.#cache.set(cacheKey2, true, result.cacheTtlMs ?? this.#cacheTtlMs);
          }
          return result;
        });
      }
      return this.#callProvider(normalizedToken, { machineId, timeoutMs });
    } catch (error) {
      return {
        ok: false,
        status: "error",
        error
      };
    }
  }
  async #callProvider(token, context) {
    const providerResult = normalizeProviderResult(await this.#entryProvider.verify(token, context));
    return {
      ok: providerResult.valid,
      status: providerResult.valid ? "valid" : "invalid",
      machineId: context.machineId,
      cached: false,
      details: providerResult.details,
      cacheable: providerResult.cacheable,
      cacheTtlMs: providerResult.cacheTtlMs
    };
  }
  async #resolveMachineId(overrideMachineId) {
    const explicitMachineId = normalizeOptionalString(overrideMachineId);
    if (explicitMachineId) {
      return explicitMachineId;
    }
    if (this.#machineId) {
      return this.#machineId;
    }
    if (!this.#machineIdResolver) {
      throw new EntryTokenValidationError("machine id is required to validate entry token");
    }
    if (this.#machineIdPromise) {
      return this.#machineIdPromise;
    }
    this.#machineIdPromise = Promise.resolve().then(() => this.#machineIdResolver()).then((resolvedMachineId) => {
      const normalizedMachineId = normalizeOptionalString(resolvedMachineId);
      if (!normalizedMachineId) {
        throw new EntryTokenValidationError("machine id is required to validate entry token");
      }
      this.#machineId = normalizedMachineId;
      return normalizedMachineId;
    }).finally(() => {
      this.#machineIdPromise = null;
    });
    return this.#machineIdPromise;
  }
};
function normalizeProviderResult(result) {
  if (typeof result === "boolean") {
    return { valid: result };
  }
  if (result && typeof result === "object" && typeof result.valid === "boolean") {
    return result;
  }
  throw new EntryTokenValidationError("entry-token provider returned an unsupported result shape", {
    details: { result }
  });
}
function normalizeOptionalString(value) {
  if (typeof value !== "string") {
    return void 0;
  }
  const trimmed = value.trim();
  return trimmed === "" ? void 0 : trimmed;
}
function requireNonEmptyToken(token) {
  const normalized = normalizeOptionalString(token);
  if (!normalized) {
    throw new TokenFormatError("entry token is required");
  }
  return normalized;
}

// ../../packages/fn-token-auth/src/validators/fnos-validator.js
var FnOsTokenValidator = class {
  #trimMainClient;
  #cache;
  #deduper;
  #enableCache;
  #cacheTtlMs;
  constructor({ trimMainClient, enableCache = true, cacheTtlMs }) {
    this.#trimMainClient = trimMainClient;
    this.#cache = new ExpiringCache();
    this.#deduper = new InflightDeduper();
    this.#enableCache = enableCache;
    this.#cacheTtlMs = cacheTtlMs;
  }
  async verify(token) {
    if (this.#enableCache) {
      const cached = this.#cache.get(token);
      if (cached) {
        return cached;
      }
      return this.#deduper.run(token, async () => {
        const identity = await this.#trimMainClient.tokenQuery(token);
        this.#cache.set(token, identity, this.#cacheTtlMs);
        return identity;
      });
    }
    return this.#trimMainClient.tokenQuery(token);
  }
};

// ../../packages/fn-token-auth/src/sdk/fn-token-auth.js
var DEFAULT_APP_ID = "com.trim.openclaw";
var DEFAULT_APP_KEY = "3D5AA9EC-E544-942B-EDE7-A9B08CAF718C";
var DEFAULT_TIMEOUT_MS2 = 2e3;
var DEFAULT_CACHE_TTL_MS = 12e4;
function createFnTokenAuth(options = {}) {
  validateOptions(options);
  const appId = getConfiguredString(options.appId) ?? DEFAULT_APP_ID;
  const appKey = getConfiguredString(options.appKey) ?? DEFAULT_APP_KEY;
  const brokerEndpoint = getConfiguredString(options.brokerEndpoint);
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS2;
  const enableCache = options.enableCache ?? true;
  const cacheTtlMs = options.cacheTtlMs ?? DEFAULT_CACHE_TTL_MS;
  const machineId = getConfiguredString(options.machineId);
  const entryEndpoint = getConfiguredString(options.entryEndpoint);
  const entryTimeoutMs = options.entryTimeoutMs ?? timeoutMs;
  const enableEntryCache = options.enableEntryCache ?? true;
  const entryCacheTtlMs = options.entryCacheTtlMs ?? DEFAULT_CACHE_TTL_MS;
  const sessionFactory = new SessionFactory();
  const transportPool = new TransportPool();
  const brokerClient = new BrokerClient({
    appId,
    appKey,
    timeoutMs,
    sessionFactory,
    transportPool,
    endpoint: brokerEndpoint
  });
  const serviceRegistry = new ServiceRegistry({ brokerClient });
  const trimAppClient = new TrimAppClient({
    appId,
    appKey,
    timeoutMs,
    sessionFactory,
    transportPool,
    serviceRegistry
  });
  const trimMainClient = new TrimMainClient({
    timeoutMs,
    sessionFactory,
    transportPool,
    serviceRegistry
  });
  const trimSysinfoClient = new TrimSysinfoClient({ trimAppClient });
  const fnosValidator = new FnOsTokenValidator({
    trimMainClient,
    enableCache,
    cacheTtlMs
  });
  const entryClient = new SacEntryClient({
    endpoint: entryEndpoint,
    timeoutMs: entryTimeoutMs
  });
  const entryProvider = options.entryTokenProvider ?? new SacEntryTokenProvider({ entryClient });
  const entryValidator = new EntryTokenValidator({
    entryProvider,
    machineId,
    machineIdResolver: async () => trimSysinfoClient.getMachineId(),
    enableCache: enableEntryCache,
    cacheTtlMs: entryCacheTtlMs,
    defaultTimeoutMs: entryTimeoutMs
  });
  return {
    async verifyFnOsToken(token) {
      return fnosValidator.verify(token);
    },
    async queryFnOsToken(token) {
      return trimMainClient.tokenQueryDetailed(token);
    },
    async verifyEntryToken(token, providerOptions = {}) {
      return entryValidator.verify(token, providerOptions);
    },
    async getMachineId() {
      return trimSysinfoClient.getMachineId();
    },
    async close() {
      await transportPool.closeAll();
    }
  };
}
function validateOptions(options) {
  if (!options || typeof options !== "object") {
    throw new ConfigurationError("createFnTokenAuth options must be an object when provided");
  }
  if (options.appId !== void 0 && typeof options.appId !== "string") {
    throw new ConfigurationError("appId must be a string when provided");
  }
  if (options.appKey !== void 0 && typeof options.appKey !== "string") {
    throw new ConfigurationError("appKey must be a string when provided");
  }
  if (options.machineId !== void 0 && typeof options.machineId !== "string") {
    throw new ConfigurationError("machineId must be a string when provided");
  }
  if (options.entryEndpoint !== void 0 && typeof options.entryEndpoint !== "string") {
    throw new ConfigurationError("entryEndpoint must be a string when provided");
  }
  if (options.entryTokenProvider !== void 0 && (!options.entryTokenProvider || typeof options.entryTokenProvider.verify !== "function")) {
    throw new ConfigurationError("entryTokenProvider must expose a verify(token, context) function");
  }
}
function getConfiguredString(value) {
  if (typeof value !== "string") {
    return void 0;
  }
  const trimmed = value.trim();
  return trimmed === "" ? void 0 : trimmed;
}

// ../../packages/fn-token-auth/src/sdk/sac-token-auth.js
var import_promises = __toESM(require("node:fs/promises"), 1);

// ../../packages/fn-token-auth/src/services/sac-fnos-client.js
var DEFAULT_SAC_ENDPOINT = "/var/run/trim_sac.socket";
var FNOS_VERIFY_PATH = "/sac/rpcproxy/v1/new-user-guide/status";
var DEFAULT_TIMEOUT_MS3 = 2e3;
var SacFnosClient = class {
  #endpoint;
  #timeoutMs;
  constructor({ endpoint = DEFAULT_SAC_ENDPOINT, timeoutMs = DEFAULT_TIMEOUT_MS3 } = {}) {
    this.#endpoint = endpoint;
    this.#timeoutMs = timeoutMs;
  }
  async verify(token, { timeoutMs = this.#timeoutMs } = {}) {
    const normalizedToken = requireNonEmptyString2(token, "fnos token is required");
    const { statusCode, bodyText } = await httpRequest({
      endpoint: this.#endpoint,
      path: FNOS_VERIFY_PATH,
      method: "GET",
      headers: {
        Authorization: `trim ${normalizedToken}`
      },
      timeoutMs
    });
    if (statusCode === 200) {
      return true;
    }
    if (statusCode === 401) {
      return false;
    }
    throw new FnOsAuthBackendError(
      `Unexpected SAC rpcproxy response: HTTP ${statusCode}`,
      { details: { statusCode, bodyText: bodyText.slice(0, 200) } }
    );
  }
};
function requireNonEmptyString2(value, message) {
  if (typeof value !== "string" || value.trim() === "") {
    throw new TokenFormatError(message);
  }
  return value.trim();
}

// ../../packages/fn-token-auth/src/validators/sac-fnos-validator.js
var SacFnosValidator = class {
  #sacFnosClient;
  #cache;
  #deduper;
  #enableCache;
  #cacheTtlMs;
  constructor({ sacFnosClient, enableCache = true, cacheTtlMs }) {
    this.#sacFnosClient = sacFnosClient;
    this.#cache = new ExpiringCache();
    this.#deduper = new InflightDeduper();
    this.#enableCache = enableCache;
    this.#cacheTtlMs = cacheTtlMs;
  }
  async verify(token) {
    if (this.#enableCache) {
      const cached = this.#cache.get(token);
      if (cached !== void 0) {
        return cached;
      }
      return this.#deduper.run(token, async () => {
        const ok2 = await this.#sacFnosClient.verify(token);
        if (!ok2) {
          throw new InvalidFnOsTokenError("fnos-token is not valid");
        }
        this.#cache.set(token, true, this.#cacheTtlMs);
        return true;
      });
    }
    const ok = await this.#sacFnosClient.verify(token);
    if (!ok) {
      throw new InvalidFnOsTokenError("fnos-token is not valid");
    }
    return true;
  }
};

// ../../packages/fn-token-auth/src/sdk/sac-token-auth.js
var DEFAULT_SAC_ENDPOINT2 = "/var/run/trim_sac.socket";
var DEFAULT_TIMEOUT_MS4 = 2e3;
var DEFAULT_CACHE_TTL_MS2 = 12e4;
var DEFAULT_DEVICE_ID_PATH = "/usr/trim/etc/machine_id";
function createSacTokenAuth(options = {}) {
  validateOptions2(options);
  const sacEndpoint = getConfiguredString2(options.sacEndpoint) ?? DEFAULT_SAC_ENDPOINT2;
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS4;
  const enableCache = options.enableCache ?? true;
  const cacheTtlMs = options.cacheTtlMs ?? DEFAULT_CACHE_TTL_MS2;
  const machineId = getConfiguredString2(options.machineId);
  const deviceIdPath = getConfiguredString2(options.deviceIdPath) ?? DEFAULT_DEVICE_ID_PATH;
  const entryEndpoint = getConfiguredString2(options.entryEndpoint) ?? sacEndpoint;
  const entryTimeoutMs = options.entryTimeoutMs ?? timeoutMs;
  const enableEntryCache = options.enableEntryCache ?? true;
  const entryCacheTtlMs = options.entryCacheTtlMs ?? DEFAULT_CACHE_TTL_MS2;
  const sacFnosClient = new SacFnosClient({
    endpoint: sacEndpoint,
    timeoutMs
  });
  const fnosValidator = new SacFnosValidator({
    sacFnosClient,
    enableCache,
    cacheTtlMs
  });
  const entryClient = new SacEntryClient({
    endpoint: entryEndpoint,
    timeoutMs: entryTimeoutMs
  });
  const entryProvider = options.entryTokenProvider ?? new SacEntryTokenProvider({ entryClient });
  const entryValidator = new EntryTokenValidator({
    entryProvider,
    machineId,
    machineIdResolver: () => readDeviceId(deviceIdPath),
    enableCache: enableEntryCache,
    cacheTtlMs: entryCacheTtlMs,
    defaultTimeoutMs: entryTimeoutMs
  });
  return {
    async verifyFnOsToken(token) {
      return fnosValidator.verify(token);
    },
    async verifyEntryToken(token, providerOptions = {}) {
      return entryValidator.verify(token, providerOptions);
    },
    async close() {
    }
  };
}
async function readDeviceId(path) {
  const content = await import_promises.default.readFile(path, "utf8");
  const trimmed = content.trim();
  if (!trimmed) {
    throw new ConfigurationError(`device id file is empty: ${path}`);
  }
  return trimmed;
}
function validateOptions2(options) {
  if (!options || typeof options !== "object") {
    throw new ConfigurationError("createSacTokenAuth options must be an object when provided");
  }
  if (options.sacEndpoint !== void 0 && typeof options.sacEndpoint !== "string") {
    throw new ConfigurationError("sacEndpoint must be a string when provided");
  }
  if (options.machineId !== void 0 && typeof options.machineId !== "string") {
    throw new ConfigurationError("machineId must be a string when provided");
  }
  if (options.entryEndpoint !== void 0 && typeof options.entryEndpoint !== "string") {
    throw new ConfigurationError("entryEndpoint must be a string when provided");
  }
  if (options.entryTokenProvider !== void 0 && (!options.entryTokenProvider || typeof options.entryTokenProvider.verify !== "function")) {
    throw new ConfigurationError("entryTokenProvider must expose a verify(token, context) function");
  }
}
function getConfiguredString2(value) {
  if (typeof value !== "string") {
    return void 0;
  }
  const trimmed = value.trim();
  return trimmed === "" ? void 0 : trimmed;
}

// src/lib/auth/fnos-auth-service.ts
var NON_RETRYABLE_ERROR_NAMES = /* @__PURE__ */ new Set([
  "InvalidFnOsTokenError",
  "TokenFormatError",
  "ConfigurationError",
  "EntryTokenProviderNotConfiguredError"
]);
var MAX_RETRIES = 1;
var RETRY_DELAY_MS = 150;
var authClient = null;
var cleanupHooksRegistered = false;
function ensureCleanupHooks() {
  if (cleanupHooksRegistered) {
    return;
  }
  cleanupHooksRegistered = true;
  const closeClient = async () => {
    if (!authClient) {
      return;
    }
    const current = authClient;
    authClient = null;
    try {
      await current.close();
    } catch (error) {
      console.error("[auth] failed to close fn-token-auth client", error);
    }
  };
  process.once("SIGINT", () => {
    void closeClient();
  });
  process.once("SIGTERM", () => {
    void closeClient();
  });
}
function getAuthClient() {
  if (!authClient) {
    if (FN_AUTH_MODE === "sac") {
      authClient = createSacTokenAuth({
        sacEndpoint: FN_AUTH_SAC_ENDPOINT,
        timeoutMs: FN_AUTH_TIMEOUT_MS,
        enableCache: true,
        cacheTtlMs: FN_AUTH_CACHE_TTL_MS,
        machineId: FN_AUTH_MACHINE_ID,
        deviceIdPath: FN_AUTH_DEVICE_ID_PATH,
        entryEndpoint: FN_AUTH_ENTRY_ENDPOINT,
        entryTimeoutMs: FN_AUTH_ENTRY_TIMEOUT_MS,
        enableEntryCache: true,
        entryCacheTtlMs: FN_AUTH_ENTRY_CACHE_TTL_MS
      });
    } else {
      authClient = createFnTokenAuth({
        timeoutMs: FN_AUTH_TIMEOUT_MS,
        enableCache: true,
        cacheTtlMs: FN_AUTH_CACHE_TTL_MS,
        machineId: FN_AUTH_MACHINE_ID,
        entryEndpoint: FN_AUTH_ENTRY_ENDPOINT,
        entryTimeoutMs: FN_AUTH_ENTRY_TIMEOUT_MS,
        enableEntryCache: true,
        entryCacheTtlMs: FN_AUTH_ENTRY_CACHE_TTL_MS
      });
    }
    ensureCleanupHooks();
  }
  return authClient;
}
function isRetryable(error) {
  if (!(error instanceof Error)) {
    return false;
  }
  return !NON_RETRYABLE_ERROR_NAMES.has(error.name);
}
function delay(ms) {
  return new Promise((resolve2) => setTimeout(resolve2, ms));
}
async function withRetry(operation) {
  let lastError;
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error;
      if (attempt < MAX_RETRIES && isRetryable(error)) {
        await delay(RETRY_DELAY_MS * (attempt + 1));
        continue;
      }
      break;
    }
  }
  throw lastError;
}
async function verifyFnOsToken(token) {
  const client = getAuthClient();
  return withRetry(() => client.verifyFnOsToken(token));
}
async function verifyEntryToken(token) {
  return withRetry(() => getAuthClient().verifyEntryToken(token));
}

// src/lib/auth/responses.ts
function wantsJson(request) {
  const accept = request.headers.get("accept") || "";
  const upgrade = request.headers.get("upgrade")?.toLowerCase();
  const pathname = new URL(request.url).pathname;
  return upgrade === "websocket" || pathname.includes("/api/") || accept.includes("application/json");
}
function jsonResponse(status, payload) {
  return Response.json(payload, {
    status,
    headers: {
      "Cache-Control": "no-store"
    }
  });
}
function htmlResponse(status, title, message) {
  const body = `<!doctype html><html><head><meta charset="utf-8"><title>${title}</title></head><body><h1>${title}</h1><p>${message}</p></body></html>`;
  return new Response(body, {
    status,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-store"
    }
  });
}
function unauthorizedResponse(request, reason) {
  if (wantsJson(request)) {
    return jsonResponse(401, { message: "Unauthorized", reason });
  }
  return htmlResponse(401, "Unauthorized", "\u8BF7\u5148\u767B\u5F55\u98DE\u725B NAS OS \u540E\u518D\u8BBF\u95EE OpenClaw monitor\u3002");
}
function forbiddenResponse(request, reason) {
  if (wantsJson(request)) {
    return jsonResponse(403, { message: "Forbidden", reason });
  }
  return htmlResponse(403, "Forbidden", "\u5F53\u524D\u8BF7\u6C42\u6765\u6E90\u65E0\u6743\u8BBF\u95EE OpenClaw monitor\u3002");
}
function serviceUnavailableResponse(request, reason) {
  if (wantsJson(request)) {
    return jsonResponse(503, { message: "Authentication service unavailable", reason });
  }
  return htmlResponse(503, "Authentication Unavailable", "fnOS \u9274\u6743\u670D\u52A1\u6682\u65F6\u4E0D\u53EF\u7528\uFF0C\u8BF7\u7A0D\u540E\u91CD\u8BD5\u3002");
}

// src/lib/auth/origin-guard.ts
function normalizeOrigin(value) {
  if (!value) {
    return null;
  }
  try {
    return new URL(value).origin;
  } catch {
    return null;
  }
}
function requestTargetOrigin(request) {
  const url = new URL(request.url);
  const forwardedProto = request.headers.get("x-forwarded-proto")?.split(",")[0]?.trim();
  const forwardedHost = request.headers.get("x-forwarded-host")?.split(",")[0]?.trim();
  const host = forwardedHost || request.headers.get("host")?.split(",")[0]?.trim();
  if (host) {
    const protocol = (forwardedProto || url.protocol.replace(/:$/, "")).replace(/:$/, "");
    return `${protocol}://${host}`;
  }
  return url.origin;
}
function requiresSameOrigin(request) {
  const method = request.method.toUpperCase();
  const upgrade = request.headers.get("upgrade")?.toLowerCase();
  if (upgrade === "websocket") {
    return true;
  }
  return !["GET", "HEAD", "OPTIONS"].includes(method);
}
function isSameOriginRequest(request) {
  const origin = normalizeOrigin(request.headers.get("origin"));
  const target = requestTargetOrigin(request);
  if (origin) {
    return origin === target;
  }
  const refererOrigin = normalizeOrigin(request.headers.get("referer"));
  if (refererOrigin) {
    return refererOrigin === target;
  }
  return false;
}

// src/lib/auth/request-auth.ts
var INVALID_FNOS_TOKEN_ERROR_NAMES = /* @__PURE__ */ new Set([
  "InvalidFnOsTokenError",
  "TokenFormatError"
]);
var INVALID_ENTRY_TOKEN_ERROR_NAMES = /* @__PURE__ */ new Set([
  "TokenFormatError"
]);
function requestLabel(request) {
  const url = new URL(request.url);
  return `${request.method.toUpperCase()} ${url.pathname}`;
}
function originFailure(request) {
  console.warn(`[auth] origin mismatch for ${requestLabel(request)}`);
  return {
    ok: false,
    reason: "origin_mismatch",
    response: forbiddenResponse(request, "origin_mismatch")
  };
}
function splitPath2(pathname) {
  return pathname.split("/").filter(Boolean);
}
function isOpenClawProxyPath(pathname) {
  const baseSegments = splitPath2(MONITOR_BASE_PATH);
  const segments = splitPath2(pathname);
  if (segments.length <= baseSegments.length) {
    return false;
  }
  for (let index = 0; index < baseSegments.length; index += 1) {
    if (segments[index] !== baseSegments[index]) {
      return false;
    }
  }
  const instanceId = segments[baseSegments.length];
  return Boolean(instanceId) && instanceId !== "api" && instanceId !== "assets";
}
function passesOriginGuard(request) {
  if (isOpenClawProxyPath(new URL(request.url).pathname)) {
    return true;
  }
  if (!FN_AUTH_REQUIRE_SAME_ORIGIN || !requiresSameOrigin(request)) {
    return true;
  }
  return isSameOriginRequest(request);
}
async function authenticateFnOsToken(request, token) {
  try {
    const result = await verifyFnOsToken(token);
    if (!result) {
      console.warn(`[auth] invalid fnOS token for ${requestLabel(request)}`);
      return { ok: false, source: "fnos", kind: "invalid" };
    }
    const identity = typeof result === "object" ? { kind: "fnos", user: result } : { kind: "fnos" };
    return { ok: true, identity };
  } catch (error) {
    const name = error instanceof Error ? error.name : "UnknownAuthError";
    const message = error instanceof Error ? error.message : String(error);
    if (INVALID_FNOS_TOKEN_ERROR_NAMES.has(name)) {
      console.warn(`[auth] invalid fnOS token for ${requestLabel(request)}: ${name}`);
      return {
        ok: false,
        source: "fnos",
        kind: "invalid"
      };
    }
    console.error(`[auth] fnOS token verification failed for ${requestLabel(request)}: ${name}: ${message}`);
    return {
      ok: false,
      source: "fnos",
      kind: "backend_error"
    };
  }
}
async function authenticateEntryToken(request, token) {
  try {
    const valid = await verifyEntryToken(token);
    if (valid) {
      return {
        ok: true,
        identity: {
          kind: "entry"
        }
      };
    }
    console.warn(`[auth] invalid entry-token for ${requestLabel(request)}`);
    return {
      ok: false,
      source: "entry",
      kind: "invalid"
    };
  } catch (error) {
    const name = error instanceof Error ? error.name : "UnknownAuthError";
    const message = error instanceof Error ? error.message : String(error);
    if (INVALID_ENTRY_TOKEN_ERROR_NAMES.has(name)) {
      console.warn(`[auth] invalid entry-token for ${requestLabel(request)}: ${name}`);
      return {
        ok: false,
        source: "entry",
        kind: "invalid"
      };
    }
    console.error(`[auth] entry-token verification failed for ${requestLabel(request)}: ${name}: ${message}`);
    return {
      ok: false,
      source: "entry",
      kind: "backend_error"
    };
  }
}
function missingFailure(source) {
  return {
    ok: false,
    source,
    kind: "missing"
  };
}
async function authenticateRequest(request) {
  const url = new URL(request.url);
  if (!FN_AUTH_ENABLED) {
    return {
      ok: true,
      identity: null,
      bypassed: true
    };
  }
  if (isAuthBypassedPath(url.pathname, request.method.toUpperCase())) {
    return {
      ok: true,
      identity: null,
      bypassed: true
    };
  }
  const fnosToken = getCookieValue(request, FN_AUTH_COOKIE_NAME);
  const entryToken = getCookieValue(request, FN_AUTH_ENTRY_COOKIE_NAME);
  const failures = [];
  if (fnosToken) {
    const fnosResult = await authenticateFnOsToken(request, fnosToken);
    if (fnosResult.ok) {
      if (!passesOriginGuard(request)) {
        return originFailure(request);
      }
      return {
        ok: true,
        identity: fnosResult.identity,
        bypassed: false
      };
    }
    failures.push(fnosResult);
  } else {
    failures.push(missingFailure("fnos"));
  }
  if (entryToken) {
    const entryResult = await authenticateEntryToken(request, entryToken);
    if (entryResult.ok) {
      if (!passesOriginGuard(request)) {
        return originFailure(request);
      }
      return {
        ok: true,
        identity: entryResult.identity,
        bypassed: false
      };
    }
    failures.push(entryResult);
  } else {
    failures.push(missingFailure("entry"));
  }
  const hasBackendError = failures.some((failure) => failure.kind === "backend_error");
  const hasCredential = Boolean(fnosToken) || Boolean(entryToken);
  if (!hasCredential) {
    console.warn(
      `[auth] missing ${FN_AUTH_COOKIE_NAME} and ${FN_AUTH_ENTRY_COOKIE_NAME} for ${requestLabel(request)}`
    );
    return {
      ok: false,
      reason: "missing_credentials",
      response: unauthorizedResponse(request, "missing_credentials")
    };
  }
  if (hasBackendError) {
    return {
      ok: false,
      reason: "auth_backend_error",
      response: serviceUnavailableResponse(request, "auth_backend_error")
    };
  }
  return {
    ok: false,
    reason: "invalid_token",
    response: unauthorizedResponse(request, "invalid_token")
  };
}

// src/lib/runtime-state.ts
var import_fs4 = require("fs");

// src/lib/instances.ts
var import_node_sqlite = require("node:sqlite");
var import_fs = require("fs");
var db = null;
function getDb() {
  if (db) {
    return db;
  }
  (0, import_fs.mkdirSync)(MONITOR_DB_DIR, { recursive: true });
  db = new import_node_sqlite.DatabaseSync(MONITOR_DB_PATH);
  db.exec(`
    CREATE TABLE IF NOT EXISTS instances (
      id TEXT PRIMARY KEY,
      owner_id TEXT NOT NULL,
      display_name TEXT NOT NULL,
      status TEXT NOT NULL,
      gateway_port INTEGER,
      proxy_base_path TEXT NOT NULL,
      data_root TEXT NOT NULL,
      install_dir TEXT NOT NULL,
      home_dir TEXT NOT NULL,
      state_dir TEXT NOT NULL,
      workspace_dir TEXT NOT NULL,
      runtime_dir TEXT NOT NULL,
      config_path TEXT NOT NULL,
      env_path TEXT NOT NULL,
      log_path TEXT NOT NULL,
      pid_path TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_instances_owner_id ON instances(owner_id);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_instances_proxy_base_path ON instances(proxy_base_path);
  `);
  return db;
}
function nowIso() {
  return (/* @__PURE__ */ new Date()).toISOString();
}
function toRecord(row) {
  return {
    id: row.id,
    ownerId: row.owner_id,
    displayName: row.display_name,
    status: row.status,
    gatewayPort: row.gateway_port,
    proxyBasePath: row.proxy_base_path,
    dataRoot: row.data_root,
    installDir: row.install_dir,
    homeDir: row.home_dir,
    stateDir: row.state_dir,
    workspaceDir: row.workspace_dir,
    runtimeDir: row.runtime_dir,
    configPath: row.config_path,
    envPath: row.env_path,
    logPath: row.log_path,
    pidPath: row.pid_path,
    createdAt: row.created_at,
    updatedAt: row.updated_at
  };
}
function buildDefaultInstance() {
  const createdAt = nowIso();
  const installDir = `${DATA_ROOT}/openclaw`;
  const homeDir = `${DATA_ROOT}/home`;
  const runtimeDir = `${DATA_ROOT}/runtime`;
  return {
    id: DEFAULT_INSTANCE_ID,
    ownerId: "system",
    displayName: "Default Gateway",
    status: "managed",
    gatewayPort: null,
    proxyBasePath: buildInstanceProxyBasePath(DEFAULT_INSTANCE_ID),
    dataRoot: DATA_ROOT,
    installDir,
    homeDir,
    stateDir: `${DATA_ROOT}/state`,
    workspaceDir: `${DATA_ROOT}/workspace`,
    runtimeDir,
    configPath: `${homeDir}/.openclaw/openclaw.json`,
    envPath: `${installDir}/.env`,
    logPath: `${installDir}/gateway.log`,
    pidPath: `${runtimeDir}/gateway.pid`,
    createdAt,
    updatedAt: createdAt
  };
}
function buildDedicatedInstance(id, ownerId, displayName) {
  const createdAt = nowIso();
  const dataRoot = `${DATA_ROOT}/instances/${id}`;
  const installDir = `${dataRoot}/openclaw`;
  const homeDir = `${dataRoot}/home`;
  const runtimeDir = `${dataRoot}/runtime`;
  return {
    id,
    ownerId,
    displayName,
    status: "created",
    gatewayPort: null,
    proxyBasePath: buildInstanceProxyBasePath(id),
    dataRoot,
    installDir,
    homeDir,
    stateDir: `${dataRoot}/state`,
    workspaceDir: `${dataRoot}/workspace`,
    runtimeDir,
    configPath: `${homeDir}/.openclaw/openclaw.json`,
    envPath: `${runtimeDir}/gateway.env`,
    logPath: `${runtimeDir}/gateway.log`,
    pidPath: `${runtimeDir}/gateway.pid`,
    createdAt,
    updatedAt: createdAt
  };
}
function persistInstance(record) {
  const database = getDb();
  database.prepare(`
      INSERT INTO instances (
        id, owner_id, display_name, status, gateway_port, proxy_base_path,
        data_root, install_dir, home_dir, state_dir, workspace_dir, runtime_dir,
        config_path, env_path, log_path, pid_path, created_at, updated_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(id) DO UPDATE SET
        owner_id = excluded.owner_id,
        display_name = excluded.display_name,
        status = excluded.status,
        gateway_port = excluded.gateway_port,
        proxy_base_path = excluded.proxy_base_path,
        data_root = excluded.data_root,
        install_dir = excluded.install_dir,
        home_dir = excluded.home_dir,
        state_dir = excluded.state_dir,
        workspace_dir = excluded.workspace_dir,
        runtime_dir = excluded.runtime_dir,
        config_path = excluded.config_path,
        env_path = excluded.env_path,
        log_path = excluded.log_path,
        pid_path = excluded.pid_path,
        updated_at = excluded.updated_at
    `).run(
    record.id,
    record.ownerId,
    record.displayName,
    record.status,
    record.gatewayPort,
    record.proxyBasePath,
    record.dataRoot,
    record.installDir,
    record.homeDir,
    record.stateDir,
    record.workspaceDir,
    record.runtimeDir,
    record.configPath,
    record.envPath,
    record.logPath,
    record.pidPath,
    record.createdAt,
    record.updatedAt
  );
}
function generateInstanceId(ownerId) {
  const normalizedOwner = ownerId.trim().toLowerCase().replace(/[^a-z0-9_-]+/g, "-").replace(/^-+|-+$/g, "");
  const suffix = crypto.randomUUID().slice(0, 8);
  return `gw_${normalizedOwner || "user"}_${suffix}`;
}
function ensureDefaultInstance() {
  const existing = getInstance(DEFAULT_INSTANCE_ID);
  if (existing) {
    return existing;
  }
  const record = buildDefaultInstance();
  persistInstance(record);
  return record;
}
function listInstances() {
  ensureDefaultInstance();
  const database = getDb();
  const rows = database.prepare(`SELECT * FROM instances ORDER BY created_at ASC`).all();
  return rows.map((row) => toRecord(row));
}
function getInstance(id) {
  const database = getDb();
  const row = database.prepare(`SELECT * FROM instances WHERE id = ? LIMIT 1`).get(id);
  return row ? toRecord(row) : null;
}
function createInstance(input) {
  ensureDefaultInstance();
  const id = generateInstanceId(input.ownerId);
  const record = buildDedicatedInstance(id, input.ownerId.trim(), input.displayName?.trim() || `${input.ownerId.trim()} Gateway`);
  persistInstance(record);
  return record;
}
function updateInstance(instanceId, patch) {
  const current = getInstance(instanceId);
  if (!current) {
    return null;
  }
  const next = {
    ...current,
    ...patch,
    updatedAt: nowIso()
  };
  persistInstance(next);
  return next;
}

// src/lib/node-fs.ts
var import_node_fs = require("node:fs");
var import_promises2 = require("node:fs/promises");
var import_node_path = require("node:path");
var MIME_TYPES = {
  ".css": "text/css; charset=utf-8",
  ".gif": "image/gif",
  ".htm": "text/html; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".jpeg": "image/jpeg",
  ".jpg": "image/jpeg",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".map": "application/json; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".txt": "text/plain; charset=utf-8",
  ".webp": "image/webp",
  ".woff": "font/woff",
  ".woff2": "font/woff2"
};
async function fileExists(path) {
  try {
    await (0, import_promises2.access)(path, import_node_fs.constants.F_OK);
    return true;
  } catch {
    return false;
  }
}
async function readTextFile(path) {
  return (0, import_promises2.readFile)(path, "utf8");
}
async function readTextFileIfExists(path) {
  try {
    return await readTextFile(path);
  } catch {
    return null;
  }
}
async function writeTextFile(path, content) {
  await (0, import_promises2.mkdir)((0, import_node_path.dirname)(path), { recursive: true });
  await (0, import_promises2.writeFile)(path, content, "utf8");
}
async function readTextSlice(path, start, endExclusive) {
  const length = Math.max(0, endExclusive - start);
  if (length === 0) {
    return "";
  }
  const handle = await (0, import_promises2.open)(path, "r");
  try {
    const buffer = Buffer.allocUnsafe(length);
    const { bytesRead } = await handle.read(buffer, 0, length, start);
    return buffer.subarray(0, bytesRead).toString("utf8");
  } finally {
    await handle.close();
  }
}
async function readStaticFile(path) {
  const [body, fileStat] = await Promise.all([(0, import_promises2.readFile)(path), (0, import_promises2.stat)(path)]);
  return {
    body,
    contentType: contentTypeForPath(path),
    size: fileStat.size
  };
}
function contentTypeForPath(path) {
  return MIME_TYPES[(0, import_node_path.extname)(path).toLowerCase()] || "application/octet-stream";
}

// src/lib/openclaw-instance.ts
var import_fs2 = require("fs");
var import_os2 = require("os");

// src/lib/config-file.ts
function stripJsonComments(text) {
  let result = "";
  let index = 0;
  let inSingleQuote = false;
  let inDoubleQuote = false;
  while (index < text.length) {
    const char = text[index];
    const next = text[index + 1];
    const previous = text[index - 1];
    if (!inDoubleQuote && char === "'" && previous !== "\\") {
      inSingleQuote = !inSingleQuote;
      result += char;
      index += 1;
      continue;
    }
    if (!inSingleQuote && char === '"' && previous !== "\\") {
      inDoubleQuote = !inDoubleQuote;
      result += char;
      index += 1;
      continue;
    }
    if (!inSingleQuote && !inDoubleQuote && char === "/" && next === "/") {
      index += 2;
      while (index < text.length && text[index] !== "\n") {
        index += 1;
      }
      continue;
    }
    if (!inSingleQuote && !inDoubleQuote && char === "/" && next === "*") {
      index += 2;
      while (index < text.length && !(text[index] === "*" && text[index + 1] === "/")) {
        index += 1;
      }
      index += 2;
      continue;
    }
    result += char;
    index += 1;
  }
  return result;
}
function normalizeConfigTextToJson(text) {
  return stripJsonComments(text).replace(/^\uFEFF/, "").replace(/([{,]\s*)([A-Za-z_$][\w$-]*)(\s*:)/g, '$1"$2"$3').replace(/'([^'\\]*(?:\\.[^'\\]*)*)'/g, (_, value) => {
    const normalized = value.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
    return `"${normalized}"`;
  }).replace(/,\s*([}\]])/g, "$1");
}
function parseLooseConfig(text) {
  const trimmed = text.trim();
  if (!trimmed) {
    return {};
  }
  try {
    return JSON.parse(trimmed);
  } catch {
    return JSON.parse(normalizeConfigTextToJson(trimmed));
  }
}
async function readLooseConfigFile(path) {
  try {
    if (!await fileExists(path)) {
      return {};
    }
    return parseLooseConfig(await readTextFile(path));
  } catch {
    return {};
  }
}

// src/lib/openclaw-platform.ts
var import_node_fs3 = require("node:fs");
var import_path = require("path");
var IS_WINDOWS = process.platform === "win32";
function managedOpenclawBinPath(installDir) {
  const binName = IS_WINDOWS ? "openclaw.cmd" : "openclaw";
  return `${installDir}/node_modules/.bin/${binName}`;
}
function prependToPath(pathValue, entry) {
  return pathValue ? `${entry}${import_path.delimiter}${pathValue}` : entry;
}
function resolveSystemOpenclawBinary() {
  try {
    const pathEntries = (process.env.PATH || "").split(import_path.delimiter).filter(Boolean);
    const candidates = IS_WINDOWS ? ["openclaw.cmd", "openclaw.exe", "openclaw.bat", "openclaw"] : ["openclaw"];
    for (const entry of pathEntries) {
      for (const candidate of candidates) {
        const fullPath = (0, import_path.join)(entry, candidate);
        try {
          (0, import_node_fs3.accessSync)(fullPath, IS_WINDOWS ? import_node_fs3.constants.F_OK : import_node_fs3.constants.X_OK);
          return fullPath;
        } catch {
        }
      }
    }
    return null;
  } catch {
    return null;
  }
}
function shouldUseSystemOpenclaw(instanceId) {
  if (instanceId !== DEFAULT_INSTANCE_ID) {
    return false;
  }
  if (process.env.OPENCLAW_USE_SYSTEM_CONFIG === "1") {
    return true;
  }
  if (process.env.OPENCLAW_USE_SYSTEM_CONFIG === "0") {
    return false;
  }
  const systemBinary = resolveSystemOpenclawBinary();
  if (!systemBinary) {
    return false;
  }
  if (process.platform === "darwin" || process.platform === "win32") {
    return isLikelyDevEnvironment();
  }
  return false;
}

// src/lib/openclaw-instance.ts
function usesSystemOpenclaw(instance) {
  return shouldUseSystemOpenclaw(instance.id);
}
function activeConfigPath(instance) {
  return usesSystemOpenclaw(instance) ? SYSTEM_OPENCLAW_CONFIG_PATH : instance.configPath;
}
function openclawEnv(instance) {
  const configPath = activeConfigPath(instance);
  if (usesSystemOpenclaw(instance)) {
    return {
      ...process.env,
      HOME: process.env.HOME || (0, import_os2.homedir)(),
      OPENCLAW_CONFIG_PATH: configPath
    };
  }
  return {
    ...process.env,
    HOME: instance.homeDir,
    OPENCLAW_CONFIG_PATH: configPath,
    PATH: prependToPath(process.env.PATH, `${instance.installDir}/node_modules/.bin`)
  };
}
function openclawBinPath(instance) {
  if (usesSystemOpenclaw(instance)) {
    return "openclaw";
  }
  return managedOpenclawBinPath(instance.installDir);
}
async function resolveOpenclawBinary(instance) {
  if (usesSystemOpenclaw(instance)) {
    return resolveSystemOpenclawBinary();
  }
  const managedBin = openclawBinPath(instance);
  return await fileExists(managedBin) ? managedBin : null;
}
async function requireOpenclawBinary(instance) {
  const resolved = await resolveOpenclawBinary(instance);
  if (!resolved) {
    throw new Error("openclaw binary not found");
  }
  return resolved;
}
function openclawSpawnCwd(instance) {
  return usesSystemOpenclaw(instance) ? void 0 : instance.installDir;
}
async function ensureInstanceDirectories(instance) {
  (0, import_fs2.mkdirSync)(instance.installDir, { recursive: true });
  (0, import_fs2.mkdirSync)(instance.homeDir, { recursive: true });
  (0, import_fs2.mkdirSync)(instance.runtimeDir, { recursive: true });
  (0, import_fs2.mkdirSync)(instance.stateDir, { recursive: true });
  (0, import_fs2.mkdirSync)(instance.workspaceDir, { recursive: true });
  (0, import_fs2.mkdirSync)(`${instance.homeDir}/.openclaw`, { recursive: true });
}
async function readJsonFile(path) {
  try {
    const config = await readLooseConfigFile(path);
    if (Object.keys(config).length > 0) {
      return config;
    }
  } catch {
    return null;
  }
  return null;
}
async function readSystemOpenclawConfig() {
  return readJsonFile(SYSTEM_OPENCLAW_CONFIG_PATH);
}
function readGatewayPortFromConfig(config) {
  const gateway = config?.gateway || {};
  const port2 = gateway.port;
  return typeof port2 === "number" && Number.isFinite(port2) ? port2 : null;
}
async function readInstancePort(instance) {
  if (usesSystemOpenclaw(instance)) {
    const systemPort = readGatewayPortFromConfig(await readSystemOpenclawConfig());
    if (systemPort) {
      return systemPort;
    }
    return null;
  }
  try {
    if (await fileExists(instance.envPath)) {
      const content = await readTextFile(instance.envPath);
      const match2 = content.match(/^PORT=(\d+)/m);
      if (match2) {
        return parseInt(match2[1], 10);
      }
    }
  } catch {
    return null;
  }
  return null;
}
async function writeInstancePort(instance, port2) {
  if (usesSystemOpenclaw(instance)) {
    const config = await readSystemOpenclawConfig() || {};
    const gateway = config.gateway || {};
    gateway.port = port2;
    config.gateway = gateway;
    await writeTextFile(activeConfigPath(instance), JSON.stringify(config, null, 2));
    return;
  }
  await ensureInstanceDirectories(instance);
  await writeTextFile(instance.envPath, `PORT=${port2}
`);
}
async function readInstanceConfig(instance) {
  const config = await readJsonFile(activeConfigPath(instance));
  if (config) {
    return config;
  }
  return {};
}
async function writeInstanceConfig(instance, config) {
  if (!usesSystemOpenclaw(instance)) {
    await ensureInstanceDirectories(instance);
  }
  await writeTextFile(activeConfigPath(instance), JSON.stringify(config, null, 2));
}

// src/lib/process-control.ts
var import_node_child_process2 = require("node:child_process");
var import_fs3 = require("fs");

// src/lib/node-process.ts
var import_node_child_process = require("node:child_process");
function createSpawnOptions(options) {
  return {
    cwd: options?.cwd,
    env: options?.env,
    stdio: ["pipe", "pipe", "pipe"]
  };
}
function spawnCommand(cmd, options) {
  const [file, ...args] = cmd;
  const child = (0, import_node_child_process.spawn)(file, args, createSpawnOptions(options));
  const exited = new Promise((resolve2, reject) => {
    child.once("error", reject);
    child.once("close", (code) => {
      resolve2(typeof code === "number" ? code : -1);
    });
  });
  return { child, exited };
}
async function collectStreamText(stream2) {
  if (!stream2) {
    return "";
  }
  const chunks = [];
  for await (const chunk of stream2) {
    chunks.push(typeof chunk === "string" ? Buffer.from(chunk) : Buffer.from(chunk));
  }
  return Buffer.concat(chunks).toString("utf8");
}
async function runCommandText(cmd, options) {
  const timeoutMs = options?.timeoutMs ?? 5e3;
  const { child, exited } = spawnCommand(cmd, options);
  let timeoutId = null;
  if (typeof options?.stdin === "string") {
    child.stdin.write(options.stdin);
  }
  child.stdin.end();
  const timeoutPromise = new Promise((_, reject) => {
    timeoutId = setTimeout(() => {
      child.kill("SIGKILL");
      reject(new Error(`Command timeout after ${timeoutMs}ms: ${cmd.join(" ")}`));
    }, timeoutMs);
  });
  try {
    const [stdout, stderr, exitCode] = await Promise.race([
      Promise.all([
        collectStreamText(child.stdout),
        collectStreamText(child.stderr),
        exited
      ]),
      timeoutPromise
    ]);
    return {
      stdout: stdout.trim(),
      stderr: stderr.trim(),
      exitCode
    };
  } catch (error) {
    return {
      stdout: "",
      stderr: error instanceof Error ? error.message : String(error),
      exitCode: -1
    };
  } finally {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
  }
}

// src/lib/process-control.ts
function isPidAlive(pid) {
  if (!pid) {
    return false;
  }
  const pidNumber = Number(pid);
  if (!Number.isInteger(pidNumber) || pidNumber <= 0) {
    return false;
  }
  try {
    process.kill(pidNumber, 0);
    return true;
  } catch {
    return false;
  }
}
async function findListeningPids(port2) {
  try {
    if (IS_WINDOWS) {
      const result2 = await runCommandText([
        "powershell.exe",
        "-NoProfile",
        "-Command",
        `$ids=@(Get-NetTCPConnection -State Listen -LocalPort ${port2} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique); $ids | ForEach-Object { $_ }`
      ]);
      if (result2.exitCode !== 0 || !result2.stdout) {
        return [];
      }
      return result2.stdout.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    }
    const result = await runCommandText(["lsof", "-ti", `TCP:${port2}`, "-sTCP:LISTEN"]);
    if (result.exitCode !== 0 || !result.stdout) {
      return [];
    }
    return result.stdout.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  } catch {
    return [];
  }
}
async function getProcessStartTime(pid) {
  if (!pid) {
    return null;
  }
  try {
    if (IS_WINDOWS) {
      const result2 = await runCommandText([
        "powershell.exe",
        "-NoProfile",
        "-Command",
        `$p=Get-Process -Id ${pid} -ErrorAction SilentlyContinue; if ($p) { $p.StartTime.ToUniversalTime().ToString('o') }`
      ]);
      if (result2.exitCode !== 0 || !result2.stdout) {
        return null;
      }
      const ts2 = Date.parse(result2.stdout);
      return Number.isNaN(ts2) ? null : ts2;
    }
    const result = await runCommandText(["ps", "-o", "lstart=", "-p", pid]);
    if (result.exitCode !== 0 || !result.stdout) {
      return null;
    }
    const ts = Date.parse(result.stdout);
    return Number.isNaN(ts) ? null : ts;
  } catch {
    return null;
  }
}
async function describeProcess(pid) {
  if (!pid) {
    return null;
  }
  try {
    if (IS_WINDOWS) {
      const result2 = await runCommandText([
        "powershell.exe",
        "-NoProfile",
        "-Command",
        `$p=Get-CimInstance Win32_Process -Filter "ProcessId = ${pid}" -ErrorAction SilentlyContinue; if ($p) { [pscustomobject]@{ ProcessId=$p.ProcessId; CommandLine=$p.CommandLine; ExecutablePath=$p.ExecutablePath } | ConvertTo-Json -Compress }`
      ]);
      if (result2.exitCode !== 0 || !result2.stdout) {
        return null;
      }
      const parsed = JSON.parse(result2.stdout);
      return {
        pid: String(parsed.ProcessId ?? pid),
        commandLine: typeof parsed.CommandLine === "string" ? parsed.CommandLine : null,
        executablePath: typeof parsed.ExecutablePath === "string" ? parsed.ExecutablePath : null
      };
    }
    let executablePath = null;
    try {
      executablePath = (0, import_fs3.readlinkSync)(`/proc/${pid}/exe`);
    } catch {
      executablePath = null;
    }
    const procfsPath = `/proc/${pid}/cmdline`;
    if (await fileExists(procfsPath)) {
      const raw2 = await readTextFileIfExists(procfsPath);
      if (!raw2) {
        return executablePath ? {
          pid,
          commandLine: null,
          executablePath
        } : null;
      }
      const commandLine = raw2.replace(/\0+/g, " ").trim();
      if (commandLine) {
        return {
          pid,
          commandLine,
          executablePath
        };
      }
    }
    const result = await runCommandText(["ps", "-o", "args=", "-p", pid]);
    if (result.exitCode !== 0 || !result.stdout) {
      return executablePath ? {
        pid,
        commandLine: null,
        executablePath
      } : null;
    }
    return {
      pid,
      commandLine: result.stdout,
      executablePath
    };
  } catch {
    return null;
  }
}
function isLikelyOpenclawProcess(snapshot) {
  if (!snapshot) {
    return false;
  }
  const joined = [snapshot.executablePath, snapshot.commandLine].filter((value) => typeof value === "string" && value.length > 0).join(" ").replace(/\\/g, "/");
  if (!joined) {
    return false;
  }
  const patterns = [
    /(?:^|[\s"'=\/])openclaw(?:\.cmd|\.ps1)?(?:$|[\s"'])/i,
    /\/node_modules\/\.bin\/openclaw(?:\.cmd|\.ps1)?(?:$|[\s"'])/i,
    /\/node_modules\/openclaw\//i
  ];
  return patterns.some((pattern) => pattern.test(joined));
}
async function pipeStreamToLog(stream2, logStream) {
  if (!stream2) {
    return;
  }
  for await (const chunk of stream2) {
    if (chunk && chunk.length > 0) {
      logStream.write(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
    }
  }
}
function spawnDetachedToLog(cmd, options) {
  const [file, ...args] = cmd;
  const proc = (0, import_node_child_process2.spawn)(file, args, {
    cwd: options.cwd,
    env: options.env,
    detached: true,
    stdio: ["ignore", "pipe", "pipe"]
  });
  const logStream = (0, import_fs3.createWriteStream)(options.logPath, { flags: "a" });
  void Promise.all([
    pipeStreamToLog(proc.stdout, logStream),
    pipeStreamToLog(proc.stderr, logStream),
    new Promise((resolve2) => {
      proc.once("close", () => resolve2());
      proc.once("error", () => resolve2());
    })
  ]).finally(() => {
    logStream.end();
  });
  proc.unref();
  return proc;
}

// src/lib/runtime-state.ts
async function resolveBinaryPath(instance) {
  return resolveOpenclawBinary(instance);
}
async function isPortListening(port2) {
  try {
    const res = await fetch(`http://127.0.0.1:${port2}`, {
      method: "HEAD",
      signal: AbortSignal.timeout(2e3)
    });
    await res.body?.cancel();
    return true;
  } catch {
    return false;
  }
}
async function readPidFile(instance) {
  try {
    if (!await fileExists(instance.pidPath)) {
      return null;
    }
    const value = (await readTextFile(instance.pidPath)).trim();
    return value || null;
  } catch {
    return null;
  }
}
function desiredStatus(installed, running) {
  if (!installed) {
    return "not_installed";
  }
  return running ? "running" : "stopped";
}
async function probeInstanceRuntime(instance) {
  const binaryPath = await resolveBinaryPath(instance);
  const installed = Boolean(binaryPath);
  const port2 = installed ? await readInstancePort(instance) ?? instance.gatewayPort : null;
  const running = port2 ? await isPortListening(port2) : false;
  let pid = await readPidFile(instance);
  let pidAlive = isPidAlive(pid);
  if (running && !pidAlive && port2) {
    const portPid = (await findListeningPids(port2))[0] || null;
    if (portPid && isPidAlive(portPid)) {
      pid = portPid;
      pidAlive = true;
    }
  }
  const startedAt = running && pidAlive ? await getProcessStartTime(pid) : null;
  return {
    installed,
    binaryPath,
    port: port2,
    running,
    pid,
    pidAlive,
    startedAt
  };
}
async function reconcileInstanceRuntime(instance, existingRuntime) {
  const runtime = existingRuntime ?? await probeInstanceRuntime(instance);
  const nextStatus = desiredStatus(runtime.installed, runtime.running);
  const nextPort = runtime.port;
  if (!runtime.running && !runtime.pidAlive) {
    try {
      (0, import_fs4.rmSync)(instance.pidPath, { force: true });
    } catch {
    }
  }
  if (instance.status !== nextStatus || instance.gatewayPort !== nextPort) {
    updateInstance(instance.id, {
      status: nextStatus,
      gatewayPort: nextPort
    });
  }
}
var reconcileTimer = null;
var reconcileInFlight = false;
async function reconcileAllInstances() {
  if (reconcileInFlight) {
    return;
  }
  reconcileInFlight = true;
  try {
    const instances = listInstances();
    await Promise.all(instances.map((instance) => reconcileInstanceRuntime(instance)));
  } finally {
    reconcileInFlight = false;
  }
}
function startRuntimeReconciler() {
  if (reconcileTimer) {
    return;
  }
  void reconcileAllInstances().catch((error) => {
    console.error("[monitor] initial runtime reconciliation failed", error);
  });
  const intervalMs = Number(process.env.MONITOR_RECONCILE_INTERVAL_MS || 3e4);
  reconcileTimer = setInterval(() => {
    void reconcileAllInstances().catch((error) => {
      console.error("[monitor] runtime reconciliation failed", error);
    });
  }, Number.isFinite(intervalMs) && intervalMs > 0 ? intervalMs : 3e4);
}

// src/lib/dev-config.ts
var import_fs5 = require("fs");
var import_path2 = require("path");
async function ensureDevModeConfig() {
  if (!shouldUseSystemOpenclaw(DEFAULT_INSTANCE_ID)) {
    return;
  }
  const configPath = SYSTEM_OPENCLAW_CONFIG_PATH;
  if (!await fileExists(configPath)) {
    console.log(`[dev-config] System OpenClaw config not found at ${configPath}`);
    return;
  }
  const config = await readLooseConfigFile(configPath);
  const gateway = config.gateway || {};
  const controlUi = gateway.controlUi || {};
  let needsUpdate = false;
  if (!controlUi.enabled) {
    console.log("[dev-config] Adding controlUi.enabled=true");
    controlUi.enabled = true;
    needsUpdate = true;
  }
  if (!controlUi.allowInsecureAuth) {
    console.log("[dev-config] Adding controlUi.allowInsecureAuth=true");
    controlUi.allowInsecureAuth = true;
    needsUpdate = true;
  }
  if (!controlUi.dangerouslyDisableDeviceAuth) {
    console.log("[dev-config] Adding controlUi.dangerouslyDisableDeviceAuth=true");
    controlUi.dangerouslyDisableDeviceAuth = true;
    needsUpdate = true;
  }
  if (!controlUi.basePath) {
    console.log("[dev-config] Adding controlUi.basePath=/");
    controlUi.basePath = "/";
    needsUpdate = true;
  }
  const allowedOrigins = Array.isArray(controlUi.allowedOrigins) ? controlUi.allowedOrigins : [];
  const devOrigins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://[::1]:3000"
  ];
  for (const origin of devOrigins) {
    if (!allowedOrigins.includes(origin)) {
      console.log(`[dev-config] Adding ${origin} to allowedOrigins`);
      allowedOrigins.push(origin);
      needsUpdate = true;
    }
  }
  if (needsUpdate) {
    controlUi.allowedOrigins = allowedOrigins;
    gateway.controlUi = controlUi;
    config.gateway = gateway;
    (0, import_fs5.mkdirSync)((0, import_path2.dirname)(configPath), { recursive: true });
    await writeTextFile(configPath, JSON.stringify(config, null, 2));
    console.log(`[dev-config] Updated system OpenClaw config at ${configPath}`);
    console.log("[dev-config] Please restart OpenClaw Gateway for changes to take effect");
  } else {
    console.log("[dev-config] System OpenClaw config is already properly configured");
  }
}

// ../../node_modules/.pnpm/ws@8.19.0/node_modules/ws/wrapper.mjs
var import_stream2 = __toESM(require_stream(), 1);
var import_receiver = __toESM(require_receiver(), 1);
var import_sender = __toESM(require_sender(), 1);
var import_websocket = __toESM(require_websocket(), 1);
var import_websocket_server = __toESM(require_websocket_server(), 1);

// src/lib/control-ui.ts
var import_path3 = require("path");
var import_fs6 = require("fs");
var configCache = /* @__PURE__ */ new Map();
var CONFIG_CACHE_TTL_MS = 5e3;
function normalizeOriginArray(value) {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.flatMap((item) => {
    if (typeof item !== "string") {
      return [];
    }
    return [item];
  });
}
function activeConfigPath2(instance) {
  return shouldUseSystemOpenclaw(instance.id) ? SYSTEM_OPENCLAW_CONFIG_PATH : instance.configPath;
}
async function readConfigFile(path) {
  const now = Date.now();
  const cached = configCache.get(path);
  if (cached && now - cached.fetchedAt < CONFIG_CACHE_TTL_MS) {
    return cached.config;
  }
  const config = await readLooseConfigFile(path);
  const result = Object.keys(config).length > 0 ? config : null;
  if (result) {
    configCache.set(path, { config: result, fetchedAt: now });
  }
  return result;
}
async function ensureControlUiAllowedOrigins(instance, source) {
  const configPath = activeConfigPath2(instance);
  if (!await fileExists(configPath)) {
    return false;
  }
  const config = await readConfigFile(configPath) || {};
  const gateway = config.gateway || {};
  const controlUi = gateway.controlUi || {};
  const nextAllowedOrigins = ["*"];
  const currentAllowedOrigins = normalizeOriginArray(controlUi.allowedOrigins);
  const unchanged = currentAllowedOrigins.length === 1 && currentAllowedOrigins[0] === "*";
  if (unchanged) {
    return false;
  }
  controlUi.allowedOrigins = nextAllowedOrigins;
  if (!controlUi.dangerouslyDisableDeviceAuth) {
    console.log("[control-ui] Adding dangerouslyDisableDeviceAuth=true to config");
    controlUi.dangerouslyDisableDeviceAuth = true;
  }
  if (!controlUi.allowInsecureAuth) {
    console.log("[control-ui] Adding allowInsecureAuth=true to config");
    controlUi.allowInsecureAuth = true;
  }
  gateway.controlUi = controlUi;
  config.gateway = gateway;
  console.log(`[control-ui] Writing config with controlUi:`, {
    enabled: controlUi.enabled,
    basePath: controlUi.basePath,
    allowInsecureAuth: controlUi.allowInsecureAuth,
    dangerouslyDisableDeviceAuth: controlUi.dangerouslyDisableDeviceAuth,
    allowedOrigins: nextAllowedOrigins
  });
  (0, import_fs6.mkdirSync)((0, import_path3.dirname)(configPath), { recursive: true });
  await writeTextFile(configPath, JSON.stringify(config, null, 2));
  configCache.delete(configPath);
  return true;
}

// src/lib/proxy-gateway.ts
var RESERVED_SEGMENTS = /* @__PURE__ */ new Set(["api", "assets"]);
var tokenCache = /* @__PURE__ */ new Map();
var TOKEN_CACHE_TTL_MS = 3e4;
var MAX_PENDING_MESSAGES = 500;
var PENDING_TIMEOUT_MS = 3e4;
var HOP_BY_HOP_HEADERS = [
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
  "content-length"
];
var WEBSOCKET_INTERNAL_HEADERS = [
  "sec-websocket-extensions",
  "sec-websocket-key",
  "sec-websocket-protocol",
  "sec-websocket-version",
  "sec-websocket-accept"
];
var CONTROL_UI_SETTINGS_KEY = "openclaw.control.settings.v1";
var CONTROL_UI_TOKEN_KEY = "openclaw.control.token.v1";
var CONTROL_UI_TOKEN_PREFIX = "openclaw.control.token.v1:";
var downstreamWss = new import_websocket_server.default({ noServer: true });
function splitPath3(pathname) {
  return pathname.split("/").filter(Boolean);
}
function matchProxyInstanceId(pathname) {
  const baseSegments = splitPath3(MONITOR_BASE_PATH);
  const segments = splitPath3(pathname);
  if (segments.length <= baseSegments.length) {
    return null;
  }
  for (let index = 0; index < baseSegments.length; index += 1) {
    if (segments[index] !== baseSegments[index]) {
      return null;
    }
  }
  const instanceId = segments[baseSegments.length];
  if (!instanceId || RESERVED_SEGMENTS.has(instanceId)) {
    return null;
  }
  return instanceId;
}
function isWebSocketRequest(request) {
  return request.headers.get("upgrade")?.toLowerCase() === "websocket";
}
async function resolveInstance(instanceId) {
  if (instanceId === DEFAULT_INSTANCE_ID) {
    return ensureDefaultInstance();
  }
  return getInstance(instanceId);
}
async function resolveGatewayToken(instance) {
  if (typeof process.env.OPENCLAW_GATEWAY_TOKEN === "string" && process.env.OPENCLAW_GATEWAY_TOKEN.length > 0) {
    return process.env.OPENCLAW_GATEWAY_TOKEN;
  }
  const now = Date.now();
  const cached = tokenCache.get(instance.id);
  if (cached && now - cached.fetchedAt < TOKEN_CACHE_TTL_MS) {
    return cached.token;
  }
  try {
    const config = await readInstanceConfig(instance);
    const gateway = config.gateway || {};
    const auth = gateway.auth || {};
    const token = typeof auth.token === "string" && auth.token.length > 0 ? auth.token : void 0;
    tokenCache.set(instance.id, { token, fetchedAt: now });
    return token;
  } catch {
    return void 0;
  }
}
async function resolveProxyTarget(request) {
  const requestUrl = new URL(request.url);
  const instanceId = matchProxyInstanceId(requestUrl.pathname);
  if (!instanceId) {
    return null;
  }
  const instance = await resolveInstance(instanceId);
  if (!instance) {
    return new Response(`OpenClaw instance not found: ${instanceId}`, { status: 404 });
  }
  await ensureControlUiAllowedOrigins(instance, {
    url: request.url,
    getHeader: (name) => request.headers.get(name)
  });
  const port2 = await readInstancePort(instance) ?? instance.gatewayPort;
  if (!port2) {
    return new Response(`OpenClaw instance is not configured: ${instanceId}`, { status: 502 });
  }
  const authToken = await resolveGatewayToken(instance);
  return {
    instance,
    port: port2,
    upstreamHttpUrl: new URL(
      `${requestUrl.pathname}${requestUrl.search}`,
      `http://127.0.0.1:${port2}`
    ),
    upstreamWsUrl: `ws://127.0.0.1:${port2}${requestUrl.pathname}${requestUrl.search}`,
    requestUrl,
    authToken
  };
}
function stripPort(host) {
  try {
    return new URL(`http://${host}`).hostname;
  } catch {
    return host;
  }
}
function forwardedForValue(request, clientIp) {
  const existing = request.headers.get("x-forwarded-for")?.trim();
  if (existing && clientIp) {
    return `${existing}, ${clientIp}`;
  }
  return existing || clientIp || null;
}
function buildBaseProxyHeaders(request, port2, proxyBasePath, clientIp) {
  const requestUrl = new URL(request.url);
  const headers = new Headers(request.headers);
  const forwardedProto = request.headers.get("x-forwarded-proto")?.split(",")[0]?.trim() || requestUrl.protocol.replace(/:$/, "");
  const forwardedHost = request.headers.get("x-forwarded-host")?.split(",")[0]?.trim() || request.headers.get("host") || requestUrl.host;
  const forwardedPort = requestUrl.port || (forwardedProto === "https" ? "443" : "80");
  const forwardedFor = forwardedForValue(request, clientIp);
  headers.set("host", `127.0.0.1:${port2}`);
  headers.set("x-forwarded-host", forwardedHost);
  headers.set("x-forwarded-proto", forwardedProto);
  headers.set("x-forwarded-port", forwardedPort);
  headers.set("x-forwarded-prefix", proxyBasePath);
  headers.set("x-forwarded-uri", `${requestUrl.pathname}${requestUrl.search}`);
  headers.set("x-real-ip", clientIp || stripPort(forwardedHost));
  if (forwardedFor) {
    headers.set("x-forwarded-for", forwardedFor);
  }
  for (const headerName of HOP_BY_HOP_HEADERS) {
    headers.delete(headerName);
  }
  return headers;
}
function buildProxyRequest(request, target, clientIp) {
  const headers = buildBaseProxyHeaders(
    request,
    target.port,
    target.instance.proxyBasePath,
    clientIp
  );
  const init = {
    method: request.method,
    headers,
    redirect: "manual",
    signal: request.signal
  };
  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = request.body;
    init.duplex = "half";
  }
  return new Request(target.upstreamHttpUrl.toString(), init);
}
function rewriteLocationHeader(responseHeaders, upstreamOrigin, requestOrigin2) {
  const location = responseHeaders.get("location");
  if (!location) {
    return;
  }
  try {
    const resolved = new URL(location, upstreamOrigin);
    if (resolved.origin !== upstreamOrigin) {
      return;
    }
    const rewritten = new URL(
      `${resolved.pathname}${resolved.search}${resolved.hash}`,
      `${requestOrigin2}/`
    );
    responseHeaders.set("location", rewritten.toString());
  } catch {
  }
}
function controlUiBootstrapScript(proxyBasePath) {
  const serializedBasePath = JSON.stringify(proxyBasePath);
  const serializedSettingsKey = JSON.stringify(CONTROL_UI_SETTINGS_KEY);
  const serializedTokenKey = JSON.stringify(CONTROL_UI_TOKEN_KEY);
  const serializedTokenPrefix = JSON.stringify(CONTROL_UI_TOKEN_PREFIX);
  return [
    "<script>",
    `window.__OPENCLAW_CONTROL_UI_BASE_PATH__ = ${serializedBasePath};`,
    "(() => {",
    "  try {",
    `    const settingsKey = ${serializedSettingsKey};`,
    "    const raw = window.localStorage.getItem(settingsKey);",
    "    if (raw) {",
    "      try {",
    "        const parsed = JSON.parse(raw);",
    "        if (parsed && typeof parsed === 'object') {",
    "          delete parsed.gatewayUrl;",
    "          delete parsed.token;",
    "          window.localStorage.setItem(settingsKey, JSON.stringify(parsed));",
    "        } else {",
    "          window.localStorage.removeItem(settingsKey);",
    "        }",
    "      } catch {",
    "        window.localStorage.removeItem(settingsKey);",
    "      }",
    "    }",
    "  } catch {}",
    "  try {",
    "    const storage = window.sessionStorage;",
    `    storage.removeItem(${serializedTokenKey});`,
    "    for (let index = storage.length - 1; index >= 0; index -= 1) {",
    "      const key = storage.key(index);",
    `      if (key && key.indexOf(${serializedTokenPrefix}) === 0) {`,
    "        storage.removeItem(key);",
    "      }",
    "    }",
    "  } catch {}",
    "})();",
    "</script>"
  ].join("");
}
function injectControlUiBootstrap(html, proxyBasePath) {
  const script = controlUiBootstrapScript(proxyBasePath);
  if (html.includes('<script type="module"')) {
    return html.replace('<script type="module"', `${script}<script type="module"`);
  }
  if (html.includes("</head>")) {
    return html.replace("</head>", `${script}</head>`);
  }
  return `${script}${html}`;
}
function formatUpstreamFetchError(error) {
  if (error instanceof Error) {
    const cause = error.cause;
    if (cause?.code && cause?.message) {
      return `${error.message} (${cause.code}: ${cause.message})`;
    }
    if (cause?.code) {
      return `${error.message} (${cause.code})`;
    }
    return error.message;
  }
  return String(error);
}
function sanitizeCloseReason(reason) {
  const trimmed = reason.trim();
  if (!trimmed) {
    return "";
  }
  return trimmed.length > 120 ? trimmed.slice(0, 120) : trimmed;
}
function shouldPatchConnectMessage(payload) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return false;
  }
  const record = payload;
  return record.type === "connect" || record.op === "connect" || record.method === "connect";
}
function injectAuthTokenIntoMessage(message, authToken) {
  if (!authToken || typeof message !== "string") {
    return message;
  }
  try {
    const payload = JSON.parse(message);
    if (!shouldPatchConnectMessage(payload)) {
      return message;
    }
    const params = payload.params && typeof payload.params === "object" && !Array.isArray(payload.params) ? payload.params : {};
    const auth = params.auth && typeof params.auth === "object" && !Array.isArray(params.auth) ? params.auth : {};
    if (typeof auth.token === "string" && auth.token.length > 0) {
      return message;
    }
    auth.token = authToken;
    params.auth = auth;
    payload.params = params;
    return JSON.stringify(payload);
  } catch {
    return message;
  }
}
function normalizeRawData(data, isBinary) {
  if (!isBinary && typeof data === "string") {
    return data;
  }
  if (Array.isArray(data)) {
    const chunks = data;
    return Buffer.concat(chunks.map((chunk) => Buffer.isBuffer(chunk) ? chunk : Buffer.from(new Uint8Array(chunk))));
  }
  if (typeof data === "string") {
    return Buffer.from(data);
  }
  return Buffer.isBuffer(data) ? data : Buffer.from(new Uint8Array(data));
}
function rawDataToText(data) {
  if (typeof data === "string") {
    return data;
  }
  if (Array.isArray(data)) {
    const chunks = data;
    return Buffer.concat(
      chunks.map((chunk) => Buffer.isBuffer(chunk) ? chunk : Buffer.from(new Uint8Array(chunk)))
    ).toString("utf8");
  }
  return Buffer.from(new Uint8Array(data)).toString("utf8");
}
function forwardMessageToUpstream(upstream, message, authToken) {
  const payload = injectAuthTokenIntoMessage(message, authToken);
  upstream.send(payload, { binary: typeof payload !== "string" });
}
function buildWebSocketHeaders(request, target, clientIp) {
  const headers = buildBaseProxyHeaders(
    request,
    target.port,
    target.instance.proxyBasePath,
    clientIp
  );
  headers.delete("host");
  for (const headerName of WEBSOCKET_INTERNAL_HEADERS) {
    headers.delete(headerName);
  }
  const serialized = {};
  for (const [key, value] of headers.entries()) {
    serialized[key] = value;
  }
  return serialized;
}
async function writeHttpResponse(socket, response) {
  const body = response.body ? Buffer.from(await response.arrayBuffer()) : Buffer.alloc(0);
  const headers = new Headers(response.headers);
  headers.set("Connection", "close");
  headers.set("Content-Length", String(body.length));
  const statusLine = `HTTP/1.1 ${response.status} ${response.statusText || "Error"}`;
  const headerLines = Array.from(headers.entries()).map(([key, value]) => `${key}: ${value}`);
  socket.write(`${statusLine}\r
${headerLines.join("\r\n")}\r
\r
`);
  socket.end(body);
}
function createUpstreamWebSocket(state) {
  if (state.protocols && state.protocols.length > 0) {
    return new import_websocket.default(state.targetUrl, state.protocols, { headers: state.headers });
  }
  return new import_websocket.default(state.targetUrl, { headers: state.headers });
}
function closeUpstreamSocket(upstream, code, reason) {
  if (!upstream || upstream.readyState >= import_websocket.default.CLOSING) {
    return;
  }
  upstream.close(code || 1e3, sanitizeCloseReason(reason || ""));
}
function setupProxyWebSocketConnection(downstream, state) {
  const upstream = createUpstreamWebSocket(state);
  state.upstream = upstream;
  upstream.on("open", () => {
    for (const message of state.pendingMessages) {
      forwardMessageToUpstream(upstream, message, state.authToken);
    }
    state.pendingMessages = [];
  });
  upstream.on("message", (data, isBinary) => {
    if (downstream.readyState !== import_websocket.default.OPEN) {
      return;
    }
    downstream.send(
      isBinary ? normalizeRawData(data, true) : rawDataToText(data),
      { binary: isBinary }
    );
  });
  upstream.on("close", (code, reason) => {
    state.upstream = void 0;
    if (downstream.readyState === import_websocket.default.OPEN || downstream.readyState === import_websocket.default.CONNECTING) {
      downstream.close(code || 1e3, sanitizeCloseReason(rawDataToText(reason)));
    }
  });
  upstream.on("error", () => {
    if (downstream.readyState === import_websocket.default.OPEN || downstream.readyState === import_websocket.default.CONNECTING) {
      downstream.close(1011, "OpenClaw upstream socket error");
    }
  });
  downstream.on("message", (data, isBinary) => {
    const message = normalizeRawData(data, isBinary);
    const activeUpstream = state.upstream;
    if (!activeUpstream) {
      return;
    }
    if (activeUpstream.readyState === import_websocket.default.CONNECTING) {
      const now = Date.now();
      if (now - state.connectStartedAt > PENDING_TIMEOUT_MS) {
        console.warn(`[proxy-gateway] Upstream connection timeout (${PENDING_TIMEOUT_MS}ms), closing`);
        downstream.close(1008, "Upstream connection timeout");
        return;
      }
      if (state.pendingMessages.length >= MAX_PENDING_MESSAGES) {
        console.warn(`[proxy-gateway] Pending messages queue full (${MAX_PENDING_MESSAGES}), closing`);
        downstream.close(1008, "Pending messages queue overflow");
        return;
      }
      state.pendingMessages.push(message);
      return;
    }
    if (activeUpstream.readyState !== import_websocket.default.OPEN) {
      return;
    }
    forwardMessageToUpstream(activeUpstream, message, state.authToken);
  });
  downstream.on("close", (code, reason) => {
    state.upstream = void 0;
    closeUpstreamSocket(upstream, code, rawDataToText(reason));
  });
  downstream.on("error", () => {
    closeUpstreamSocket(upstream, 1011, "Monitor downstream socket error");
  });
}
async function maybeProxyHttpRequest(request, clientIp) {
  const target = await resolveProxyTarget(request);
  if (!target) {
    return null;
  }
  if (target instanceof Response) {
    return target;
  }
  try {
    const upstreamResponse = await fetch(buildProxyRequest(request, target, clientIp));
    const responseHeaders = new Headers(upstreamResponse.headers);
    rewriteLocationHeader(
      responseHeaders,
      target.upstreamHttpUrl.origin,
      target.requestUrl.origin
    );
    const contentType = responseHeaders.get("content-type")?.toLowerCase() || "";
    if (contentType.includes("text/html")) {
      const html = await upstreamResponse.text();
      const patchedHtml = injectControlUiBootstrap(html, target.instance.proxyBasePath);
      responseHeaders.delete("content-length");
      responseHeaders.set("cache-control", "no-store");
      return new Response(patchedHtml, {
        status: upstreamResponse.status,
        statusText: upstreamResponse.statusText,
        headers: responseHeaders
      });
    }
    return new Response(upstreamResponse.body, {
      status: upstreamResponse.status,
      statusText: upstreamResponse.statusText,
      headers: responseHeaders
    });
  } catch (error) {
    const message = formatUpstreamFetchError(error);
    return new Response(`OpenClaw upstream request failed: ${message}`, {
      status: 502
    });
  }
}
async function maybeHandleProxyWebSocketUpgrade(request, incoming, socket, head, clientIp) {
  if (!isWebSocketRequest(request)) {
    return false;
  }
  const target = await resolveProxyTarget(request);
  if (!target) {
    return false;
  }
  if (target instanceof Response) {
    await writeHttpResponse(socket, target);
    return true;
  }
  const protocols = request.headers.get("sec-websocket-protocol")?.split(",").map((value) => value.trim()).filter(Boolean);
  const state = {
    targetUrl: target.upstreamWsUrl,
    headers: buildWebSocketHeaders(request, target, clientIp),
    protocols: protocols && protocols.length > 0 ? protocols : void 0,
    authToken: target.authToken,
    pendingMessages: [],
    connectStartedAt: Date.now()
  };
  downstreamWss.handleUpgrade(incoming, socket, head, (downstream) => {
    setupProxyWebSocketConnection(downstream, state);
  });
  return true;
}

// ../../node_modules/.pnpm/hono@4.12.5/node_modules/hono/dist/utils/stream.js
var StreamingApi = class {
  writer;
  encoder;
  writable;
  abortSubscribers = [];
  responseReadable;
  /**
   * Whether the stream has been aborted.
   */
  aborted = false;
  /**
   * Whether the stream has been closed normally.
   */
  closed = false;
  constructor(writable, _readable) {
    this.writable = writable;
    this.writer = writable.getWriter();
    this.encoder = new TextEncoder();
    const reader = _readable.getReader();
    this.abortSubscribers.push(async () => {
      await reader.cancel();
    });
    this.responseReadable = new ReadableStream({
      async pull(controller) {
        const { done, value } = await reader.read();
        done ? controller.close() : controller.enqueue(value);
      },
      cancel: () => {
        this.abort();
      }
    });
  }
  async write(input) {
    try {
      if (typeof input === "string") {
        input = this.encoder.encode(input);
      }
      await this.writer.write(input);
    } catch {
    }
    return this;
  }
  async writeln(input) {
    await this.write(input + "\n");
    return this;
  }
  sleep(ms) {
    return new Promise((res) => setTimeout(res, ms));
  }
  async close() {
    try {
      await this.writer.close();
    } catch {
    }
    this.closed = true;
  }
  async pipe(body) {
    this.writer.releaseLock();
    await body.pipeTo(this.writable, { preventClose: true });
    this.writer = this.writable.getWriter();
  }
  onAbort(listener) {
    this.abortSubscribers.push(listener);
  }
  /**
   * Abort the stream.
   * You can call this method when stream is aborted by external event.
   */
  abort() {
    if (!this.aborted) {
      this.aborted = true;
      this.abortSubscribers.forEach((subscriber) => subscriber());
    }
  }
};

// ../../node_modules/.pnpm/hono@4.12.5/node_modules/hono/dist/helper/streaming/utils.js
var isOldBunVersion = () => {
  const version = typeof Bun !== "undefined" ? Bun.version : void 0;
  if (version === void 0) {
    return false;
  }
  const result = version.startsWith("1.1") || version.startsWith("1.0") || version.startsWith("0.");
  isOldBunVersion = () => result;
  return result;
};

// ../../node_modules/.pnpm/hono@4.12.5/node_modules/hono/dist/helper/streaming/sse.js
var SSEStreamingApi = class extends StreamingApi {
  constructor(writable, readable) {
    super(writable, readable);
  }
  async writeSSE(message) {
    const data = await resolveCallback(message.data, HtmlEscapedCallbackPhase.Stringify, false, {});
    const dataLines = data.split(/\r\n|\r|\n/).map((line) => {
      return `data: ${line}`;
    }).join("\n");
    for (const key of ["event", "id", "retry"]) {
      if (message[key] && /[\r\n]/.test(message[key])) {
        throw new Error(`${key} must not contain "\\r" or "\\n"`);
      }
    }
    const sseData2 = [
      message.event && `event: ${message.event}`,
      dataLines,
      message.id && `id: ${message.id}`,
      message.retry && `retry: ${message.retry}`
    ].filter(Boolean).join("\n") + "\n\n";
    await this.write(sseData2);
  }
};
var run = async (stream2, cb, onError) => {
  try {
    await cb(stream2);
  } catch (e) {
    if (e instanceof Error && onError) {
      await onError(e, stream2);
      await stream2.writeSSE({
        event: "error",
        data: e.message
      });
    } else {
      console.error(e);
    }
  } finally {
    stream2.close();
  }
};
var contextStash = /* @__PURE__ */ new WeakMap();
var streamSSE = (c, cb, onError) => {
  const { readable, writable } = new TransformStream();
  const stream2 = new SSEStreamingApi(writable, readable);
  if (isOldBunVersion()) {
    c.req.raw.signal.addEventListener("abort", () => {
      if (!stream2.closed) {
        stream2.abort();
      }
    });
  }
  contextStash.set(stream2.responseReadable, c);
  c.header("Transfer-Encoding", "chunked");
  c.header("Content-Type", "text/event-stream");
  c.header("Cache-Control", "no-cache");
  c.header("Connection", "keep-alive");
  run(stream2, cb, onError);
  return c.newResponse(stream2.responseReadable);
};

// src/routes/gateway.ts
var import_fs7 = require("fs");
var import_path4 = require("path");
var app = new Hono2();
var TAIL_READ_BYTES = 64 * 1024;
function findLatestSystemRuntimeLogPath() {
  try {
    const candidates = (0, import_fs7.readdirSync)(SYSTEM_OPENCLAW_RUNTIME_LOG_DIR).filter((entry) => /^openclaw-\d{4}-\d{2}-\d{2}\.log$/.test(entry)).map((entry) => {
      const path = (0, import_path4.join)(SYSTEM_OPENCLAW_RUNTIME_LOG_DIR, entry);
      return {
        path,
        mtimeMs: (0, import_fs7.statSync)(path).mtimeMs
      };
    }).sort((a, b) => b.mtimeMs - a.mtimeMs);
    return candidates[0]?.path ?? null;
  } catch {
    return null;
  }
}
async function resolveGatewayLogPath() {
  const instance = ensureDefaultInstance();
  const managedPath = instance.logPath;
  if (await fileExists(managedPath)) {
    return { path: managedPath, source: "managed", exists: true };
  }
  if (shouldUseSystemOpenclaw(instance.id)) {
    const sources = await Promise.all([
      (async () => {
        if (!await fileExists(SYSTEM_OPENCLAW_LOG_PATH)) {
          return null;
        }
        return {
          path: SYSTEM_OPENCLAW_LOG_PATH,
          source: "system-wrapper",
          mtimeMs: (0, import_fs7.statSync)(SYSTEM_OPENCLAW_LOG_PATH).mtimeMs
        };
      })(),
      (async () => {
        const runtimePath = findLatestSystemRuntimeLogPath();
        if (!runtimePath) {
          return null;
        }
        if (!await fileExists(runtimePath)) {
          return null;
        }
        return {
          path: runtimePath,
          source: "system-runtime",
          mtimeMs: (0, import_fs7.statSync)(runtimePath).mtimeMs
        };
      })()
    ]);
    const bestSource = sources.filter((candidate) => candidate !== null).sort((a, b) => b.mtimeMs - a.mtimeMs)[0];
    if (bestSource) {
      return { path: bestSource.path, source: bestSource.source, exists: true };
    }
  }
  return {
    path: managedPath,
    source: "managed",
    exists: false
  };
}
async function readTailLines(logPath, maxLines) {
  let fileSize;
  try {
    fileSize = (0, import_fs7.statSync)(logPath).size;
  } catch {
    return [];
  }
  if (fileSize === 0) {
    return [];
  }
  const readStart = Math.max(0, fileSize - TAIL_READ_BYTES);
  const chunk = await readTextSlice(logPath, readStart, fileSize);
  const lines = chunk.split("\n").filter((line) => line.trim());
  if (readStart > 0 && lines.length > 0) {
    lines.shift();
  }
  return lines.slice(-maxLines);
}
app.get("/logs", async (c) => {
  const abortSignal = c.req.raw.signal;
  return streamSSE(c, async (stream2) => {
    const instance = ensureDefaultInstance();
    const { path: logPath, source, exists } = await resolveGatewayLogPath();
    if (exists) {
      const lines = await readTailLines(logPath, 100);
      for (const line of lines) {
        if (abortSignal.aborted) return;
        await stream2.writeSSE({ data: line, event: "log" });
      }
    } else {
      const systemManaged = shouldUseSystemOpenclaw(instance.id);
      const missingMessage = systemManaged ? `[monitor] No gateway log file found. Checked managed log ${instance.logPath}, system wrapper log ${SYSTEM_OPENCLAW_LOG_PATH}, and runtime logs under ${SYSTEM_OPENCLAW_RUNTIME_LOG_DIR}.` : `[monitor] No gateway log file at ${logPath} yet. Logs will appear after monitor starts the managed gateway and the file is created.`;
      await stream2.writeSSE({ data: missingMessage, event: "log" });
    }
    if (source === "system-wrapper") {
      await stream2.writeSSE({
        data: `[monitor] Streaming system gateway wrapper log from ${logPath}.`,
        event: "log"
      });
    } else if (source === "system-runtime") {
      await stream2.writeSSE({
        data: `[monitor] Streaming system OpenClaw runtime log from ${logPath}.`,
        event: "log"
      });
    }
    let position = exists ? (0, import_fs7.statSync)(logPath).size : 0;
    let buffer = "";
    const heartbeat = setInterval(async () => {
      try {
        if (abortSignal.aborted) {
          clearInterval(heartbeat);
          return;
        }
        await stream2.writeSSE({ data: "", event: "heartbeat" });
      } catch {
        clearInterval(heartbeat);
      }
    }, 5e3);
    try {
      while (!abortSignal.aborted) {
        await new Promise((resolve2) => setTimeout(resolve2, 1e3));
        if (abortSignal.aborted) break;
        let size = 0;
        try {
          size = (0, import_fs7.statSync)(logPath).size;
        } catch {
          continue;
        }
        if (size < position) {
          position = 0;
          buffer = "";
        }
        if (size === position) {
          continue;
        }
        const chunk = await readTextSlice(logPath, position, size);
        position = size;
        buffer += chunk;
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          if (abortSignal.aborted) break;
          if (line.trim()) {
            await stream2.writeSSE({ data: line, event: "log" });
          }
        }
      }
    } catch {
    } finally {
      clearInterval(heartbeat);
    }
  });
});
var gateway_default = app;

// src/routes/install.ts
var import_fs8 = require("fs");
var app2 = new Hono2();
var SHUTDOWN_GRACE_PERIOD_MS = 15e3;
var FORCE_KILL_WAIT_MS = 5e3;
var STARTUP_WAIT_MS = 3e4;
var COUNTDOWN_TICK_MS = 1e3;
var MAX_INSTALL_QUEUE_SIZE = 1e3;
function sseData(event, payload) {
  return JSON.stringify({ event, ...payload });
}
function sleep(ms) {
  return new Promise((resolve2) => setTimeout(resolve2, ms));
}
function emitLog(enqueue, type, line) {
  enqueue(sseData("log", { type, line }));
}
function emitState(enqueue, phase, label, extra) {
  enqueue(sseData("state", { phase, label, ...extra || {} }));
}
async function readLines(stream2, type, onLine) {
  let buffer = "";
  try {
    for await (const chunk of stream2 || []) {
      buffer += typeof chunk === "string" ? chunk : Buffer.from(chunk).toString("utf8");
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (line.length > 0) {
          onLine(sseData("log", { type, line }));
        }
      }
    }
    if (buffer.length > 0) {
      onLine(sseData("log", { type, line: buffer }));
    }
  } finally {
  }
}
function randomPort() {
  return Math.floor(Math.random() * 4e4) + 1e4;
}
async function deploySoulMd(instance, enqueue) {
  if (!SOUL_MD_SRC) {
    return;
  }
  try {
    const content = await readTextFileIfExists(SOUL_MD_SRC);
    if (!content) {
      return;
    }
    const workspaceDest = `${instance.workspaceDir}/SOUL.md`;
    (0, import_fs8.mkdirSync)(instance.workspaceDir, { recursive: true });
    await writeTextFile(workspaceDest, content);
    emitLog(enqueue, "info", `Deployed SOUL.md to workspace ${workspaceDest}`);
    const legacyDest = `${instance.homeDir}/.openclaw/SOUL.md`;
    try {
      (0, import_fs8.mkdirSync)(`${instance.homeDir}/.openclaw`, { recursive: true });
      await writeTextFile(legacyDest, content);
      emitLog(enqueue, "info", `Mirrored SOUL.md to legacy path ${legacyDest}`);
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      emitLog(enqueue, "stderr", `Failed to mirror SOUL.md to legacy path: ${msg}`);
    }
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    emitLog(enqueue, "stderr", `Failed to deploy SOUL.md: ${msg}`);
  }
}
async function ensureOpenclawConfig(instance, port2, enqueue, c) {
  await ensureInstanceDirectories(instance);
  const config = await readInstanceConfig(instance);
  const gateway = config.gateway || {};
  gateway.mode = "local";
  gateway.port = port2;
  gateway.bind = "loopback";
  gateway.trustedProxies = ["127.0.0.1", "::1"];
  const auth = gateway.auth || {};
  if (typeof auth.token !== "string" || auth.token.length === 0) {
    auth.token = crypto.randomUUID().replace(/-/g, "");
  }
  gateway.auth = auth;
  const controlUi = gateway.controlUi || {};
  controlUi.enabled = true;
  controlUi.basePath = instance.proxyBasePath;
  controlUi.allowInsecureAuth = true;
  controlUi.dangerouslyDisableDeviceAuth = true;
  controlUi.allowedOrigins = ["*"];
  gateway.controlUi = controlUi;
  const agents = config.agents || {};
  const defaults = agents.defaults || {};
  defaults.workspace = instance.workspaceDir;
  agents.defaults = defaults;
  config.gateway = gateway;
  config.agents = agents;
  await writeInstanceConfig(instance, config);
  enqueue(
    sseData("log", {
      type: "info",
      line: `Config written: ${activeConfigPath(instance)}`
    })
  );
  enqueue(
    sseData("log", {
      type: "info",
      line: `[gateway] seeded gateway.controlUi.allowedOrigins ${JSON.stringify(controlUi.allowedOrigins)}`
    })
  );
}
async function listGatewayPids(instance, port2) {
  const pids = /* @__PURE__ */ new Set();
  if (port2) {
    for (const pid of await findListeningPids(port2)) {
      if (pid) {
        pids.add(pid);
      }
    }
  }
  try {
    const pidFromFile = (0, import_fs8.readFileSync)(instance.pidPath, "utf8").trim();
    if (pidFromFile) {
      pids.add(pidFromFile);
    }
  } catch {
  }
  return pids;
}
async function filterValidatedGatewayPids(pids, enqueue, warnedPids) {
  const validated = /* @__PURE__ */ new Set();
  for (const pid of pids) {
    const snapshot = await describeProcess(pid);
    if (isLikelyOpenclawProcess(snapshot)) {
      validated.add(pid);
      continue;
    }
    const detail = snapshot?.commandLine || snapshot?.executablePath || "unknown process";
    if (!warnedPids || !warnedPids.has(pid)) {
      warnedPids?.add(pid);
      emitLog(enqueue, "error", `Refusing to signal PID ${pid} because it is not recognized as an OpenClaw process: ${detail}`);
    }
  }
  return validated;
}
function fallbackGatewayPids(pids, enqueue, context) {
  const fallback = /* @__PURE__ */ new Set();
  for (const pid of pids) {
    if (pid === String(process.pid)) {
      emitLog(enqueue, "error", `Refusing fallback stop for PID ${pid} because it matches the monitor process itself.`);
      continue;
    }
    fallback.add(pid);
  }
  if (fallback.size > 0) {
    emitLog(
      enqueue,
      "info",
      `Falling back to configured-port PID ownership for ${context}: ${Array.from(fallback).join(", ")}`
    );
  }
  return fallback;
}
async function waitForGatewayState(predicate, options) {
  const deadline = Date.now() + options.timeoutMs;
  let lastCountdown = null;
  while (true) {
    if (await predicate()) {
      emitState(options.enqueue, options.phase, options.label, {
        countdownSeconds: 0,
        countdownTotalSeconds: Math.ceil(options.timeoutMs / 1e3)
      });
      return true;
    }
    const remainingMs = deadline - Date.now();
    if (remainingMs <= 0) {
      return false;
    }
    const countdownSeconds = Math.ceil(remainingMs / 1e3);
    if (countdownSeconds !== lastCountdown) {
      lastCountdown = countdownSeconds;
      emitState(options.enqueue, options.phase, options.label, {
        countdownSeconds,
        countdownTotalSeconds: Math.ceil(options.timeoutMs / 1e3)
      });
    }
    await sleep(Math.min(COUNTDOWN_TICK_MS, remainingMs));
  }
}
async function gracefulStopGateway(instance, enqueue, reason) {
  const existingPort = await readInstancePort(instance);
  const warnedPids = /* @__PURE__ */ new Set();
  const initialPidCandidates = await listGatewayPids(instance, existingPort);
  let initialPids = await filterValidatedGatewayPids(initialPidCandidates, enqueue, warnedPids);
  const initiallyListening = existingPort ? await isPortListening(existingPort) : false;
  if (initialPidCandidates.size === 0 && !initiallyListening) {
    updateInstance(instance.id, { status: "stopped" });
    try {
      (0, import_fs8.rmSync)(instance.pidPath, { force: true });
    } catch {
    }
    emitState(enqueue, "stopped", `${instance.displayName} \u5DF2\u505C\u6B62`, {
      countdownSeconds: 0,
      countdownTotalSeconds: Math.ceil(SHUTDOWN_GRACE_PERIOD_MS / 1e3)
    });
    emitLog(
      enqueue,
      "info",
      existingPort ? `No running gateway process found on port ${existingPort}. Marked instance as stopped.` : "No running gateway process found. Marked instance as stopped."
    );
    return false;
  }
  if (initialPids.size === 0) {
    initialPids = fallbackGatewayPids(
      initialPidCandidates,
      enqueue,
      existingPort ? `${instance.displayName} on configured port ${existingPort}` : instance.displayName
    );
  }
  if (initialPids.size === 0) {
    throw new Error(
      existingPort ? `Refusing to stop ${instance.displayName}: no validated OpenClaw process found for configured port ${existingPort}, and no safe fallback PID was available.` : `Refusing to stop ${instance.displayName}: no validated OpenClaw process found.`
    );
  }
  const verb = reason === "stop" ? "\u5173\u95ED" : "\u91CD\u542F\u524D\u5173\u95ED";
  emitState(enqueue, "stopping", `\u6B63\u5728\u4F18\u96C5${verb} ${instance.displayName}`, {
    countdownSeconds: Math.ceil(SHUTDOWN_GRACE_PERIOD_MS / 1e3),
    countdownTotalSeconds: Math.ceil(SHUTDOWN_GRACE_PERIOD_MS / 1e3)
  });
  emitLog(
    enqueue,
    "info",
    `Sending SIGTERM to gateway (PID: ${Array.from(initialPids).join(", ") || "unknown"}${existingPort ? `, port: ${existingPort}` : ""})`
  );
  for (const pid of initialPids) {
    const pidNumber = Number(pid);
    if (Number.isInteger(pidNumber) && pidNumber > 0) {
      try {
        process.kill(pidNumber, "SIGTERM");
      } catch {
      }
    }
  }
  const stoppedGracefully = await waitForGatewayState(
    async () => {
      const activePids = await filterValidatedGatewayPids(await listGatewayPids(instance, existingPort), enqueue, warnedPids);
      const pidAlive = Array.from(activePids).some((pid) => isPidAlive(pid));
      const portBusy = existingPort ? await isPortListening(existingPort) : false;
      return !pidAlive && !portBusy;
    },
    {
      timeoutMs: SHUTDOWN_GRACE_PERIOD_MS,
      phase: "stopping",
      label: `\u7B49\u5F85 ${instance.displayName} \u5B8C\u6210\u4F18\u96C5\u5173\u95ED`,
      enqueue
    }
  );
  if (!stoppedGracefully) {
    const forceKillCandidates = await listGatewayPids(instance, existingPort);
    let forceKillPids = await filterValidatedGatewayPids(forceKillCandidates, enqueue, warnedPids);
    if (forceKillPids.size === 0) {
      forceKillPids = fallbackGatewayPids(
        forceKillCandidates,
        enqueue,
        existingPort ? `${instance.displayName} on configured port ${existingPort} during forced stop` : `${instance.displayName} during forced stop`
      );
    }
    emitState(enqueue, "forcing-stop", `${instance.displayName} \u4F18\u96C5\u5173\u95ED\u8D85\u65F6\uFF0C\u5F00\u59CB\u5F3A\u5236\u7ED3\u675F`, {
      countdownSeconds: Math.ceil(FORCE_KILL_WAIT_MS / 1e3),
      countdownTotalSeconds: Math.ceil(FORCE_KILL_WAIT_MS / 1e3)
    });
    emitLog(
      enqueue,
      "error",
      `Graceful shutdown timed out after ${Math.ceil(SHUTDOWN_GRACE_PERIOD_MS / 1e3)}s. Forcing termination.`
    );
    for (const pid of forceKillPids) {
      const pidNumber = Number(pid);
      if (Number.isInteger(pidNumber) && pidNumber > 0) {
        try {
          process.kill(pidNumber, "SIGKILL");
        } catch {
        }
      }
    }
    const killed = await waitForGatewayState(
      async () => {
        const activePids = await filterValidatedGatewayPids(await listGatewayPids(instance, existingPort), enqueue, warnedPids);
        const pidAlive = Array.from(activePids).some((pid) => isPidAlive(pid));
        const portBusy = existingPort ? await isPortListening(existingPort) : false;
        return !pidAlive && !portBusy;
      },
      {
        timeoutMs: FORCE_KILL_WAIT_MS,
        phase: "forcing-stop",
        label: `\u7B49\u5F85 ${instance.displayName} \u5B8C\u6210\u5F3A\u5236\u5173\u95ED`,
        enqueue
      }
    );
    if (!killed) {
      updateInstance(instance.id, { status: "error" });
      throw new Error(
        `${instance.displayName} did not exit after graceful shutdown timeout and forced termination.`
      );
    }
  }
  updateInstance(instance.id, { status: "stopped" });
  try {
    (0, import_fs8.rmSync)(instance.pidPath, { force: true });
  } catch {
  }
  emitState(enqueue, "stopped", `${instance.displayName} \u5DF2\u505C\u6B62`, {
    countdownSeconds: 0,
    countdownTotalSeconds: Math.ceil(SHUTDOWN_GRACE_PERIOD_MS / 1e3)
  });
  emitLog(enqueue, "success", `Gateway stopped cleanly${existingPort ? ` on port ${existingPort}` : ""}.`);
  return true;
}
async function startOpenclaw(instance, port2, enqueue, c) {
  await ensureOpenclawConfig(instance, port2, enqueue, c);
  const openclawBinary = await requireOpenclawBinary(instance);
  const cmd = [
    openclawBinary,
    "gateway",
    "run",
    "--port",
    String(port2),
    "--bind",
    "loopback"
  ];
  emitState(enqueue, "starting", `\u6B63\u5728\u542F\u52A8 ${instance.displayName}`, {
    countdownSeconds: Math.ceil(STARTUP_WAIT_MS / 1e3),
    countdownTotalSeconds: Math.ceil(STARTUP_WAIT_MS / 1e3)
  });
  emitLog(enqueue, "info", `Starting gateway: ${cmd.join(" ")}`);
  const proc = spawnDetachedToLog(cmd, {
    env: openclawEnv(instance),
    cwd: openclawSpawnCwd(instance),
    logPath: instance.logPath
  });
  await writeTextFile(instance.pidPath, `${proc.pid}
`);
  const listening = await waitForGatewayState(
    async () => isPortListening(port2),
    {
      timeoutMs: STARTUP_WAIT_MS,
      phase: "starting",
      label: `\u7B49\u5F85 ${instance.displayName} \u5C31\u7EEA`,
      enqueue
    }
  );
  if (!listening) {
    const content = await readTextFileIfExists(instance.logPath);
    if (content) {
      for (const line of content.split("\n").slice(-15)) {
        if (line.trim()) {
          emitLog(enqueue, "stderr", line);
        }
      }
    }
    updateInstance(instance.id, { status: "error" });
    throw new Error(`Gateway did not start on port ${port2}. See gateway logs for details.`);
  }
  updateInstance(instance.id, { gatewayPort: port2, status: "running" });
  emitState(enqueue, "running", `${instance.displayName} \u5DF2\u5C31\u7EEA`, {
    countdownSeconds: 0,
    countdownTotalSeconds: Math.ceil(STARTUP_WAIT_MS / 1e3)
  });
  emitLog(enqueue, "success", `openclaw gateway is running on port ${port2}`);
}
async function getVersion(instance) {
  try {
    const binaryPath = await requireOpenclawBinary(instance);
    const result = await runCommandText([binaryPath, "--version"], {
      env: openclawEnv(instance),
      cwd: openclawSpawnCwd(instance)
    });
    const version = result.stdout.trim();
    return version || null;
  } catch {
    return null;
  }
}
async function hasOpenclawBinary(instance) {
  return await resolveOpenclawBinary(instance) !== null;
}
function resolveInstance2(instanceId) {
  if (!instanceId) {
    return ensureDefaultInstance();
  }
  return getInstance(instanceId);
}
app2.post("/", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const method = body.method || "npm";
  const action = body.action || "install";
  const instance = resolveInstance2(body.instanceId);
  if (!instance) {
    return c.json({ message: "Instance not found" }, 404);
  }
  return streamSSE(c, async (stream2) => {
    const queue = [];
    let streamClosed = false;
    let writeChain = Promise.resolve();
    function enqueue(data) {
      if (queue.length >= MAX_INSTALL_QUEUE_SIZE) {
        console.warn(`[install] Queue size limit reached (${MAX_INSTALL_QUEUE_SIZE}), dropping message`);
        return;
      }
      queue.push(data);
      scheduleFlush();
    }
    function scheduleFlush() {
      writeChain = writeChain.then(async () => {
        if (streamClosed) {
          return;
        }
        await flushQueue();
      }).catch((error) => {
        streamClosed = true;
        console.error("[install] Failed to flush SSE queue:", error);
      });
    }
    async function flushQueue() {
      while (queue.length > 0) {
        const data = queue.shift();
        try {
          await stream2.writeSSE({ data, event: "message" });
        } catch (error) {
          streamClosed = true;
          console.error("[install] Failed to write SSE:", error);
          break;
        }
      }
    }
    const heartbeat = setInterval(() => {
      if (streamClosed || queue.length > 0) {
        return;
      }
      writeChain = writeChain.then(async () => {
        if (!streamClosed) {
          await stream2.writeSSE({ data: "", event: "heartbeat" });
        }
      }).catch((error) => {
        streamClosed = true;
        console.error("[install] SSE heartbeat failed:", error);
      });
    }, 5e3);
    try {
      if (action === "start" || action === "restart") {
        emitLog(
          enqueue,
          "info",
          action === "restart" ? `Restarting ${instance.displayName}...` : `Starting ${instance.displayName}...`
        );
        if (!await hasOpenclawBinary(instance)) {
          enqueue(
            sseData("error", {
              message: "openclaw binary not found. Please install first."
            })
          );
          await writeChain;
          return;
        }
        if (action === "restart") {
          await gracefulStopGateway(instance, enqueue, "restart");
        }
        let port2 = await readInstancePort(instance);
        if (!port2) {
          port2 = randomPort();
          await writeInstancePort(instance, port2);
        }
        await startOpenclaw(instance, port2, enqueue, c);
        const version = await getVersion(instance);
        enqueue(sseData("complete", { success: true, version, port: port2, instanceId: instance.id }));
        await writeChain;
        return;
      }
      if (action === "stop") {
        if (usesSystemOpenclaw(instance)) {
          enqueue(
            sseData("error", {
              message: "System OpenClaw mode is attached to your existing gateway. Stop is disabled in monitor to avoid terminating the shared transparent gateway. Stop it manually if you really intend to shut it down."
            })
          );
          await writeChain;
          return;
        }
        emitLog(enqueue, "info", `Stopping ${instance.displayName}...`);
        await gracefulStopGateway(instance, enqueue, "stop");
        enqueue(sseData("complete", { success: true, stopped: true, instanceId: instance.id }));
        await writeChain;
        return;
      }
      if (action === "reinstall") {
        if (usesSystemOpenclaw(instance)) {
          enqueue(
            sseData("log", {
              type: "info",
              line: `System OpenClaw mode detected. Skipping local reinstall and restarting the system gateway instead.`
            })
          );
          await gracefulStopGateway(instance, enqueue, "reinstall");
          let port2 = await readInstancePort(instance);
          if (!port2) {
            port2 = randomPort();
            await writeInstancePort(instance, port2);
          }
          await startOpenclaw(instance, port2, enqueue, c);
          const version = await getVersion(instance);
          enqueue(sseData("complete", { success: true, version, port: port2, instanceId: instance.id }));
          await writeChain;
          return;
        }
        enqueue(
          sseData("log", {
            type: "info",
            line: `Checking updates for ${instance.displayName} and upgrading managed installation in place...`
          })
        );
        await gracefulStopGateway(instance, enqueue, "reinstall");
      }
      enqueue(
        sseData("log", {
          type: "info",
          line: `Starting installation with method: ${method}`
        })
      );
      if (usesSystemOpenclaw(instance)) {
        enqueue(
          sseData("log", {
            type: "info",
            line: `System OpenClaw mode detected. Monitor will use the existing OpenClaw installation and ~/.openclaw config instead of creating a managed local install.`
          })
        );
        if (!await hasOpenclawBinary(instance)) {
          enqueue(
            sseData("error", {
              message: "System OpenClaw binary not found. Install OpenClaw globally first, then use Start/Restart from monitor."
            })
          );
          await writeChain;
          return;
        }
        let port2 = await readInstancePort(instance);
        if (!port2) {
          port2 = randomPort();
          await writeInstancePort(instance, port2);
        }
        await startOpenclaw(instance, port2, enqueue, c);
        const version = await getVersion(instance);
        enqueue(sseData("complete", { success: true, version, port: port2, instanceId: instance.id }));
        await writeChain;
        return;
      }
      const npmCacheDir = `${instance.installDir}/.npm-cache`;
      const env = {
        ...process.env,
        SHARP_IGNORE_GLOBAL_LIBVIPS: "1",
        HOME: instance.homeDir,
        npm_config_cache: npmCacheDir
      };
      await ensureInstanceDirectories(instance);
      (0, import_fs8.mkdirSync)(npmCacheDir, { recursive: true });
      const packageJsonPath = `${instance.installDir}/package.json`;
      if (!await fileExists(packageJsonPath)) {
        await writeTextFile(packageJsonPath, JSON.stringify({
          name: "managed-openclaw",
          private: true
        }, null, 2));
      }
      let cmd;
      if (method === "npm") {
        cmd = [
          "npm",
          "install",
          "--prefix",
          instance.installDir,
          "--registry",
          OPENCLAW_NPM_REGISTRY,
          "openclaw@latest"
        ];
        enqueue(
          sseData("log", {
            type: "info",
            line: `Install target: ${instance.installDir}`
          })
        );
        enqueue(
          sseData("log", {
            type: "info",
            line: `Using package registry: ${OPENCLAW_NPM_REGISTRY}`
          })
        );
      } else {
        cmd = [
          "bash",
          "-c",
          "curl -fsSL https://openclaw.ai/install.sh | bash"
        ];
      }
      enqueue(
        sseData("log", { type: "info", line: `Running: ${cmd.join(" ")}` })
      );
      const { child, exited } = spawnCommand(cmd, {
        env,
        cwd: instance.installDir
      });
      const stdoutDone = readLines(child.stdout, "stdout", enqueue);
      const stderrDone = readLines(child.stderr, "stderr", enqueue);
      await Promise.all([stdoutDone, stderrDone]);
      const exitCode = await exited;
      await writeChain;
      if (exitCode === 0) {
        enqueue(
          sseData("log", {
            type: "success",
            line: "npm install completed successfully!"
          })
        );
        await deploySoulMd(instance, enqueue);
        let port2 = await readInstancePort(instance);
        if (!port2) {
          port2 = randomPort();
          await writeInstancePort(instance, port2);
          enqueue(
            sseData("log", {
              type: "info",
              line: `Assigned openclaw port: ${port2}`
            })
          );
        } else {
          enqueue(
            sseData("log", {
              type: "info",
              line: `Reusing configured openclaw port: ${port2}`
            })
          );
        }
        await startOpenclaw(instance, port2, enqueue, c);
        const version = await getVersion(instance);
        enqueue(sseData("complete", { success: true, version, port: port2, instanceId: instance.id }));
      } else {
        updateInstance(instance.id, { status: "install_failed" });
        enqueue(
          sseData("error", {
            message: `Installation failed with exit code ${exitCode}`,
            exitCode
          })
        );
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      enqueue(sseData("error", { message }));
    } finally {
      clearInterval(heartbeat);
      await writeChain;
      await flushQueue();
      streamClosed = true;
    }
  });
});
var install_default = app2;

// src/lib/status.ts
var versionCache = /* @__PURE__ */ new Map();
var VERSION_CACHE_TTL_MS = 3e5;
async function runCommand(instance, cmd) {
  return runCommandText(cmd, {
    env: openclawEnv(instance)
  });
}
function requestOrigin(c) {
  const url = new URL(c.req.url);
  const forwardedProto = c.req.header("x-forwarded-proto")?.split(",")[0]?.trim();
  const forwardedHost = c.req.header("x-forwarded-host")?.split(",")[0]?.trim();
  if (forwardedHost) {
    return `${(forwardedProto || url.protocol.replace(/:$/, "")).replace(/:$/, "")}://${forwardedHost}`;
  }
  return url.origin;
}
function buildBootstrapUrl(pageUrl, token) {
  const bootstrapUrl = new URL(pageUrl);
  bootstrapUrl.searchParams.set("token", token);
  return bootstrapUrl.toString();
}
function requestHostname(c) {
  const forwardedHost = c.req.header("x-forwarded-host")?.split(",")[0]?.trim();
  const host = forwardedHost || c.req.header("host")?.split(",")[0]?.trim();
  if (host) {
    try {
      return new URL(`http://${host}`).hostname;
    } catch {
      return host;
    }
  }
  return "127.0.0.1";
}
async function getInstanceStatus(instance, c) {
  let installed = false;
  let running = false;
  let version = null;
  let binaryPath = null;
  let port2 = null;
  let startedAt = null;
  let dashboardUrl = null;
  let dashboardTokenizedUrl = null;
  let proxyDashboardUrl = null;
  let proxyDashboardTokenizedUrl = null;
  let gatewayTokenPresent = false;
  const runtime = await probeInstanceRuntime(instance);
  installed = runtime.installed;
  binaryPath = runtime.binaryPath;
  port2 = runtime.port;
  running = runtime.running;
  startedAt = runtime.startedAt;
  if (installed && binaryPath) {
    const now = Date.now();
    const cached = versionCache.get(binaryPath);
    if (cached && now - cached.fetchedAt < VERSION_CACHE_TTL_MS) {
      version = cached.version;
    } else {
      try {
        const ver = await runCommand(instance, [binaryPath, "--version"]);
        if (ver.exitCode === 0) {
          version = ver.stdout;
          versionCache.set(binaryPath, { version, fetchedAt: now });
        }
      } catch {
      }
    }
  }
  await reconcileInstanceRuntime(instance, runtime);
  if (installed) {
    await ensureControlUiAllowedOrigins(instance, {
      url: c.req.url,
      getHeader: (name) => c.req.header(name)
    });
    const config = await readInstanceConfig(instance);
    const gateway = config.gateway || {};
    const controlUi = gateway.controlUi || {};
    const auth = gateway.auth || {};
    const configuredUiBasePath = normalizePublicBasePath(
      typeof controlUi.basePath === "string" && controlUi.basePath.length > 0 ? controlUi.basePath : "/"
    );
    const proxyUiBasePath = normalizePublicBasePath(instance.proxyBasePath);
    proxyDashboardUrl = new URL(proxyUiBasePath, `${requestOrigin(c)}/`).toString();
    if (port2) {
      const directOrigin = `${new URL(c.req.url).protocol}//${requestHostname(c)}:${port2}`;
      dashboardUrl = new URL(configuredUiBasePath, `${directOrigin}/`).toString();
    }
    const token = typeof process.env.OPENCLAW_GATEWAY_TOKEN === "string" && process.env.OPENCLAW_GATEWAY_TOKEN.length > 0 ? process.env.OPENCLAW_GATEWAY_TOKEN : typeof auth.token === "string" ? auth.token : null;
    gatewayTokenPresent = Boolean(token);
    if (token) {
      if (dashboardUrl) {
        dashboardTokenizedUrl = buildBootstrapUrl(dashboardUrl, token);
      }
      if (proxyDashboardUrl) {
        proxyDashboardTokenizedUrl = buildBootstrapUrl(proxyDashboardUrl, token);
      }
    }
  }
  return {
    instanceId: instance.id,
    ownerId: instance.ownerId,
    displayName: instance.displayName,
    proxyBasePath: instance.proxyBasePath,
    systemMode: usesSystemOpenclaw(instance),
    installed,
    running,
    version,
    binaryPath,
    port: port2,
    startedAt,
    dashboardUrl,
    dashboardTokenizedUrl,
    proxyDashboardUrl,
    proxyDashboardTokenizedUrl,
    gatewayTokenPresent
  };
}

// src/routes/instances.ts
var app3 = new Hono2();
app3.get("/", async (c) => {
  const instances = await Promise.all(
    listInstances().map(async (instance) => getInstanceStatus(instance, c))
  );
  return c.json({ instances });
});
app3.get("/:instanceId", async (c) => {
  const instance = getInstance(c.req.param("instanceId"));
  if (!instance) {
    return c.json({ message: "Instance not found" }, 404);
  }
  return c.json(await getInstanceStatus(instance, c));
});
app3.post("/", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const ownerId = body.ownerId?.trim();
  if (!ownerId) {
    return c.json({ message: "ownerId is required" }, 400);
  }
  const instance = createInstance({
    ownerId,
    displayName: body.displayName
  });
  return c.json(instance, 201);
});
var instances_default = app3;

// src/lib/channels.ts
var import_fs9 = require("fs");
var import_promises3 = require("fs/promises");

// src/lib/cli-json.ts
function isLikelyJsonStart(source, index) {
  const start = source[index];
  if (start !== "{" && start !== "[") {
    return false;
  }
  let cursor = index + 1;
  while (cursor < source.length && /\s/.test(source[cursor])) {
    cursor += 1;
  }
  if (cursor >= source.length) {
    return false;
  }
  const next = source[cursor];
  if (start === "{") {
    return next === '"' || next === "}";
  }
  return next === "{" || next === "[" || next === '"' || next === "]" || next === "-" || /[0-9tfn]/.test(next);
}
function parseJsonFromCommandOutput(stdout) {
  const trimmed = stdout.trim();
  if (!trimmed) {
    throw new Error("Command returned empty output");
  }
  try {
    return JSON.parse(trimmed);
  } catch {
  }
  for (let index = 0; index < stdout.length; index += 1) {
    if (!isLikelyJsonStart(stdout, index)) {
      continue;
    }
    const candidate = stdout.slice(index).trim();
    try {
      return JSON.parse(candidate);
    } catch {
    }
  }
  throw new Error("Invalid JSON payload in command output");
}

// src/lib/channels.ts
function asObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}
function asString(value) {
  return typeof value === "string" && value.trim().length > 0 ? value.trim() : null;
}
function asBoolean(value, fallback) {
  return typeof value === "boolean" ? value : fallback;
}
function asNumber(value, fallback) {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}
async function readConfigFile2(path) {
  return readLooseConfigFile(path);
}
async function resolveOpenclawBinary2(instance) {
  return requireOpenclawBinary(instance);
}
async function tryResolveOpenclawBinary(instance) {
  return resolveOpenclawBinary(instance);
}
async function runOpenclawCommand(instance, args) {
  const bin = await resolveOpenclawBinary2(instance);
  return runCommandText([bin, ...args], {
    env: openclawEnv(instance),
    cwd: openclawSpawnCwd(instance)
  });
}
async function runOpenclawJsonCommand(instance, args) {
  const result = await runOpenclawCommand(instance, args);
  if (result.exitCode !== 0) {
    throw new Error(result.stderr || result.stdout || `openclaw ${args.join(" ")} failed`);
  }
  try {
    return parseJsonFromCommandOutput(result.stdout);
  } catch {
    throw new Error(`Invalid JSON from openclaw ${args.join(" ")}`);
  }
}
async function getActiveConfigPath(instance) {
  return activeConfigPath(instance);
}
function makeJsonArg(value) {
  return JSON.stringify(value);
}
async function setConfigValue(instance, path, value) {
  const result = await runOpenclawCommand(instance, ["config", "set", path, makeJsonArg(value), "--strict-json"]);
  if (result.exitCode !== 0) {
    throw new Error(result.stderr || result.stdout || `Failed to set ${path}`);
  }
}
function assignOrDelete(target, key, value) {
  if (value === void 0 || value === null || typeof value === "string" && value.trim().length === 0 || Array.isArray(value) && value.length === 0) {
    delete target[key];
    return;
  }
  target[key] = value;
}
function buildFeishuSnapshot(feishuConfigRaw) {
  const accountsRaw = asObject(feishuConfigRaw.accounts);
  const firstAccount = asObject(Object.values(accountsRaw)[0]);
  const appId = asString(feishuConfigRaw.appId) || asString(firstAccount.appId) || "";
  const appSecretConfigured = Boolean(asString(feishuConfigRaw.appSecret) || asString(firstAccount.appSecret));
  return {
    configured: Object.keys(feishuConfigRaw).length > 0,
    appId,
    appSecretConfigured,
    enabled: asBoolean(feishuConfigRaw.enabled, false),
    connectionMode: asString(feishuConfigRaw.connectionMode) === "webhook" ? "webhook" : "websocket",
    dmPolicy: (() => {
      const value = asString(feishuConfigRaw.dmPolicy);
      return value === "allowlist" || value === "open" || value === "disabled" ? value : "pairing";
    })(),
    groupPolicy: (() => {
      const value = asString(feishuConfigRaw.groupPolicy);
      return value === "open" || value === "disabled" ? value : "allowlist";
    })(),
    requireMention: asBoolean(feishuConfigRaw.requireMention, true)
  };
}
function buildDingtalkSnapshot(dingtalkConfigRaw, gatewayConfigRaw) {
  const gatewayAuth = asObject(gatewayConfigRaw.auth);
  const gatewayHttp = asObject(gatewayConfigRaw.http);
  const endpoints = asObject(gatewayHttp.endpoints);
  const chatCompletions = asObject(endpoints.chatCompletions);
  return {
    configured: Object.keys(dingtalkConfigRaw).length > 0,
    clientId: asString(dingtalkConfigRaw.clientId) || "",
    clientSecretConfigured: Boolean(asString(dingtalkConfigRaw.clientSecret)),
    gatewayTokenConfigured: Boolean(asString(dingtalkConfigRaw.gatewayToken)),
    gatewayPasswordConfigured: Boolean(asString(dingtalkConfigRaw.gatewayPassword)),
    gatewayAuthMode: asString(gatewayAuth.mode),
    gatewayAuthTokenConfigured: Boolean(asString(gatewayAuth.token)),
    sessionTimeout: asNumber(dingtalkConfigRaw.sessionTimeout, 18e5),
    chatCompletionsEnabled: asBoolean(chatCompletions.enabled, false)
  };
}
function buildWecomSnapshot(wecomConfigRaw) {
  return {
    configured: Object.keys(wecomConfigRaw).length > 0,
    botId: asString(wecomConfigRaw.botId) || "",
    secretConfigured: Boolean(asString(wecomConfigRaw.secret)),
    enabled: asBoolean(wecomConfigRaw.enabled, false),
    websocketUrl: asString(wecomConfigRaw.websocketUrl) || "wss://openws.work.weixin.qq.com",
    dmPolicy: (() => {
      const value = asString(wecomConfigRaw.dmPolicy);
      return value === "allowlist" || value === "open" || value === "disabled" ? value : "pairing";
    })()
  };
}
function normalizeFeishuInput(input) {
  const appId = input.appId.trim();
  if (!appId) {
    throw new Error("\u98DE\u4E66 App ID \u4E0D\u80FD\u4E3A\u7A7A");
  }
  return {
    appId,
    appSecret: typeof input.appSecret === "string" ? input.appSecret.trim() : null
  };
}
function normalizeWecomInput(input) {
  const botId = input.botId.trim();
  if (!botId) {
    throw new Error("\u4F01\u4E1A\u5FAE\u4FE1 Bot ID \u4E0D\u80FD\u4E3A\u7A7A");
  }
  return {
    botId,
    secret: typeof input.secret === "string" ? input.secret.trim() : null
  };
}
async function getChannelsConfig(instance) {
  const binaryPath = await tryResolveOpenclawBinary(instance);
  const activeConfigPath3 = await getActiveConfigPath(instance);
  const configExists = (0, import_fs9.existsSync)(activeConfigPath3);
  const config = await readConfigFile2(activeConfigPath3);
  const channelsConfig = asObject(config.channels);
  const feishuConfig = asObject(channelsConfig.feishu);
  const wecomConfig = asObject(channelsConfig.wecom);
  const dingtalkConfig = asObject(channelsConfig["dingtalk-connector"]);
  const gatewayConfig = asObject(config.gateway);
  let validation = {
    valid: true,
    path: activeConfigPath3
  };
  if (binaryPath && configExists) {
    try {
      validation = await runOpenclawJsonCommand(
        instance,
        ["config", "validate", "--json"]
      );
    } catch (error) {
      validation = {
        valid: false,
        path: activeConfigPath3,
        errors: [error instanceof Error ? error.message : String(error)]
      };
    }
  }
  return {
    configPath: validation.path || activeConfigPath3,
    configExists,
    validation: {
      valid: Boolean(validation.valid),
      message: Array.isArray(validation.errors) && validation.errors.length > 0 ? validation.errors.join("; ") : typeof validation.error === "string" && validation.error.length > 0 ? validation.error : void 0
    },
    configuredChannelIds: Object.keys(channelsConfig).sort(),
    feishu: buildFeishuSnapshot(feishuConfig),
    wecom: buildWecomSnapshot(wecomConfig),
    dingtalk: buildDingtalkSnapshot(dingtalkConfig, gatewayConfig)
  };
}
function normalizeDingtalkInput(input) {
  const clientId = input.clientId.trim();
  if (!clientId) {
    throw new Error("\u9489\u9489 Client ID \u4E0D\u80FD\u4E3A\u7A7A");
  }
  return {
    clientId,
    clientSecret: typeof input.clientSecret === "string" ? input.clientSecret.trim() : null
  };
}
function pluginDescriptor(channelKey) {
  if (channelKey === "feishu") {
    return {
      channelKey,
      pluginId: "feishu",
      label: "\u98DE\u4E66",
      packageSpec: "@openclaw/feishu",
      requiresRestart: true,
      docUrl: "https://docs.openclaw.ai/channels/feishu",
      note: "OpenClaw \u5B98\u65B9\u6587\u6863\u8BF4\u660E\u5F53\u524D\u7248\u672C\u901A\u5E38\u5DF2\u5185\u7F6E Feishu\uFF1B\u65E7\u7248\u672C\u6216\u81EA\u5B9A\u4E49\u5B89\u88C5\u53EF\u624B\u52A8\u5B89\u88C5\u3002"
    };
  }
  if (channelKey === "wecom") {
    return {
      channelKey,
      pluginId: "wecom-openclaw-plugin",
      label: "\u4F01\u4E1A\u5FAE\u4FE1",
      packageSpec: "@wecom/wecom-openclaw-plugin",
      requiresRestart: true,
      docUrl: "https://open.work.weixin.qq.com/help?doc_id=21657",
      note: "\u63D2\u4EF6 ID \u662F wecom-openclaw-plugin\uFF0C\u914D\u7F6E\u91CC\u7684 channel key \u662F wecom\uFF1B\u4E24\u8005\u4E0D\u662F\u540C\u4E00\u4E2A\u5B57\u6BB5\u3002"
    };
  }
  if (channelKey === "dingtalk") {
    return {
      channelKey,
      pluginId: "dingtalk-connector",
      label: "\u9489\u9489",
      packageSpec: "@dingtalk-real-ai/dingtalk-connector",
      requiresRestart: true,
      docUrl: "https://open.dingtalk.com/document/dingstart/build-dingtalk-ai-employees",
      note: "\u8FD9\u91CC\u6309\u4F60\u63D0\u4F9B\u7684\u63D2\u4EF6\u5305\u540D\u6267\u884C\u5B89\u88C5\uFF1B\u5B57\u6BB5\u8BBE\u8BA1\u5E94\u4EE5\u9489\u9489\u5F00\u653E\u5E73\u53F0\u6587\u6863\u548C\u63D2\u4EF6\u81EA\u8EAB schema \u4E3A\u51C6\u3002"
    };
  }
  return {
    channelKey,
    pluginId: "dingtalk-connector",
    label: "\u9489\u9489",
    packageSpec: "@dingtalk-real-ai/dingtalk-connector",
    requiresRestart: true,
    docUrl: "https://open.dingtalk.com/document/dingstart/build-dingtalk-ai-employees",
    note: "\u8FD9\u91CC\u6309\u4F60\u63D0\u4F9B\u7684\u63D2\u4EF6\u5305\u540D\u6267\u884C\u5B89\u88C5\uFF1B\u5B57\u6BB5\u8BBE\u8BA1\u5E94\u4EE5\u9489\u9489\u5F00\u653E\u5E73\u53F0\u6587\u6863\u548C\u63D2\u4EF6\u81EA\u8EAB schema \u4E3A\u51C6\u3002"
  };
}
async function getChannelPlugins(instance) {
  let pluginListStdout = "";
  const binaryPath = await tryResolveOpenclawBinary(instance);
  if (binaryPath) {
    const result = await runOpenclawCommand(instance, ["plugins", "list"]);
    if (result.exitCode === 0) {
      pluginListStdout = result.stdout.toLowerCase();
    }
  }
  function listed(descriptor, aliases) {
    const patterns = [
      descriptor.packageSpec.toLowerCase(),
      descriptor.pluginId.toLowerCase(),
      descriptor.channelKey.toLowerCase(),
      ...aliases.map((alias) => alias.toLowerCase())
    ];
    return patterns.some((pattern) => pattern.length > 0 && pluginListStdout.includes(pattern));
  }
  const plugins = [
    (() => {
      const descriptor = pluginDescriptor("feishu");
      const installed = listed(descriptor, ["lark"]);
      return {
        ...descriptor,
        installed,
        source: installed ? "package" : "unknown"
      };
    })(),
    (() => {
      const descriptor = pluginDescriptor("wecom");
      const installed = listed(descriptor, ["wecom-openclaw-plugin", "wechat-work", "work-wechat"]);
      return {
        ...descriptor,
        installed,
        source: installed ? "package" : "unknown"
      };
    })(),
    (() => {
      const descriptor = pluginDescriptor("dingtalk");
      const installed = listed(descriptor, ["dingtalk-connector", "dingding"]);
      return {
        ...descriptor,
        installed,
        source: installed ? "package" : "unknown"
      };
    })()
  ];
  return { plugins };
}
async function installChannelPlugin(instance, payload) {
  if (!await tryResolveOpenclawBinary(instance)) {
    throw new Error("OpenClaw \u5C1A\u672A\u5B89\u88C5\uFF0C\u65E0\u6CD5\u5B89\u88C5\u6E20\u9053\u63D2\u4EF6\u3002");
  }
  if (payload.channelKey !== "feishu" && payload.channelKey !== "wecom" && payload.channelKey !== "dingtalk") {
    throw new Error("Unsupported channel plugin");
  }
  const descriptor = pluginDescriptor(payload.channelKey);
  const result = await runOpenclawCommand(instance, ["plugins", "install", descriptor.packageSpec]);
  if (result.exitCode !== 0) {
    throw new Error(result.stderr || result.stdout || `\u5B89\u88C5 ${descriptor.packageSpec} \u5931\u8D25`);
  }
  return {
    channelKey: descriptor.channelKey,
    pluginId: descriptor.pluginId,
    label: descriptor.label,
    packageSpec: descriptor.packageSpec,
    requiresRestart: descriptor.requiresRestart,
    stdout: result.stdout,
    stderr: result.stderr
  };
}
async function saveChannelsConfig(instance, payload) {
  if (!await tryResolveOpenclawBinary(instance)) {
    throw new Error("OpenClaw \u5C1A\u672A\u5B89\u88C5\uFF0C\u65E0\u6CD5\u4FDD\u5B58\u6D88\u606F\u6E20\u9053\u914D\u7F6E\u3002");
  }
  if (payload.wecom && typeof payload.wecom === "object") {
    const normalized2 = normalizeWecomInput(payload.wecom);
    const configPath2 = await getActiveConfigPath(instance);
    const currentConfig2 = await readConfigFile2(configPath2);
    const channelsRaw2 = asObject(currentConfig2.channels);
    const currentWecom = asObject(channelsRaw2.wecom);
    const currentSecret = asString(currentWecom.secret);
    const nextSecret = normalized2.secret || currentSecret;
    if (!nextSecret) {
      throw new Error("\u4F01\u4E1A\u5FAE\u4FE1 Secret \u4E0D\u80FD\u4E3A\u7A7A");
    }
    const nextWecom = { ...currentWecom };
    nextWecom.botId = normalized2.botId;
    nextWecom.secret = nextSecret;
    nextWecom.enabled = true;
    nextWecom.websocketUrl = asString(currentWecom.websocketUrl) || "wss://openws.work.weixin.qq.com";
    nextWecom.dmPolicy = "pairing";
    const originalSnapshot2 = {
      exists: await fileExists(configPath2),
      text: await readTextFileIfExists(configPath2) || ""
    };
    try {
      await setConfigValue(instance, "channels.wecom", nextWecom);
      const validation = await runOpenclawJsonCommand(
        instance,
        ["config", "validate", "--json"]
      );
      if (!validation.valid) {
        throw new Error(
          Array.isArray(validation.errors) && validation.errors.length > 0 ? validation.errors.join("; ") : validation.error || "Config validation failed"
        );
      }
    } catch (error) {
      if (originalSnapshot2.exists) {
        await writeTextFile(configPath2, originalSnapshot2.text);
      } else if (await fileExists(configPath2)) {
        await (0, import_promises3.rm)(configPath2, { force: true });
      }
      throw error;
    }
    return getChannelsConfig(instance);
  }
  if (payload.dingtalk && typeof payload.dingtalk === "object") {
    const normalized2 = normalizeDingtalkInput(payload.dingtalk);
    const configPath2 = await getActiveConfigPath(instance);
    const currentConfig2 = await readConfigFile2(configPath2);
    const channelsRaw2 = asObject(currentConfig2.channels);
    const currentDingtalk = asObject(channelsRaw2["dingtalk-connector"]);
    const gatewayRaw = asObject(currentConfig2.gateway);
    const currentAuth = asObject(gatewayRaw.auth);
    const currentHttp = asObject(gatewayRaw.http);
    const currentEndpoints = asObject(currentHttp.endpoints);
    const currentChatCompletions = asObject(currentEndpoints.chatCompletions);
    const currentClientSecret = asString(currentDingtalk.clientSecret);
    const currentGatewayToken = asString(currentAuth.token) || asString(currentDingtalk.gatewayToken);
    const currentGatewayPassword = asString(currentDingtalk.gatewayPassword);
    const currentSessionTimeout = asNumber(currentDingtalk.sessionTimeout, 18e5);
    const nextClientSecret = normalized2.clientSecret || currentClientSecret;
    if (!nextClientSecret) {
      throw new Error("\u9489\u9489 Client Secret \u4E0D\u80FD\u4E3A\u7A7A");
    }
    const nextGatewayToken = currentGatewayToken || crypto.randomUUID().replace(/-/g, "");
    const nextGatewayPassword = currentGatewayPassword;
    const nextDingtalk = { ...currentDingtalk };
    nextDingtalk.clientId = normalized2.clientId;
    nextDingtalk.clientSecret = nextClientSecret;
    nextDingtalk.gatewayToken = nextGatewayToken;
    nextDingtalk.sessionTimeout = currentSessionTimeout;
    assignOrDelete(nextDingtalk, "gatewayPassword", nextGatewayPassword);
    const nextGatewayAuth = {
      ...currentAuth,
      mode: "token",
      token: nextGatewayToken
    };
    const nextGatewayHttp = {
      ...currentHttp,
      endpoints: {
        ...currentEndpoints,
        chatCompletions: {
          ...currentChatCompletions,
          enabled: true
        }
      }
    };
    const originalSnapshot2 = {
      exists: await fileExists(configPath2),
      text: await readTextFileIfExists(configPath2) || ""
    };
    try {
      await setConfigValue(instance, "channels.dingtalk-connector", nextDingtalk);
      await setConfigValue(instance, "gateway.auth", nextGatewayAuth);
      await setConfigValue(instance, "gateway.http", nextGatewayHttp);
      const validation = await runOpenclawJsonCommand(
        instance,
        ["config", "validate", "--json"]
      );
      if (!validation.valid) {
        throw new Error(
          Array.isArray(validation.errors) && validation.errors.length > 0 ? validation.errors.join("; ") : validation.error || "Config validation failed"
        );
      }
    } catch (error) {
      if (originalSnapshot2.exists) {
        await writeTextFile(configPath2, originalSnapshot2.text);
      } else if (await fileExists(configPath2)) {
        await (0, import_promises3.rm)(configPath2, { force: true });
      }
      throw error;
    }
    return getChannelsConfig(instance);
  }
  if (!payload.feishu || typeof payload.feishu !== "object") {
    throw new Error("\u7F3A\u5C11\u53EF\u4FDD\u5B58\u7684\u6E20\u9053\u914D\u7F6E");
  }
  const normalized = normalizeFeishuInput(payload.feishu);
  const configPath = await getActiveConfigPath(instance);
  const currentConfig = await readConfigFile2(configPath);
  const channelsRaw = asObject(currentConfig.channels);
  const currentFeishu = asObject(channelsRaw.feishu);
  const currentAccounts = asObject(currentFeishu.accounts);
  const firstAccount = asObject(Object.values(currentAccounts)[0]);
  const nextFeishu = { ...currentFeishu };
  const currentAppSecret = asString(currentFeishu.appSecret) || asString(firstAccount.appSecret);
  const nextAppSecret = normalized.appSecret || currentAppSecret;
  if (!nextAppSecret) {
    throw new Error("\u98DE\u4E66 App Secret \u4E0D\u80FD\u4E3A\u7A7A");
  }
  nextFeishu.appId = normalized.appId;
  nextFeishu.appSecret = nextAppSecret;
  nextFeishu.enabled = true;
  nextFeishu.connectionMode = "websocket";
  nextFeishu.dmPolicy = "pairing";
  nextFeishu.groupPolicy = "allowlist";
  nextFeishu.requireMention = true;
  const originalSnapshot = {
    exists: await fileExists(configPath),
    text: await readTextFileIfExists(configPath) || ""
  };
  try {
    await setConfigValue(instance, "channels.feishu", nextFeishu);
    const validation = await runOpenclawJsonCommand(
      instance,
      ["config", "validate", "--json"]
    );
    if (!validation.valid) {
      throw new Error(
        Array.isArray(validation.errors) && validation.errors.length > 0 ? validation.errors.join("; ") : validation.error || "Config validation failed"
      );
    }
  } catch (error) {
    if (originalSnapshot.exists) {
      await writeTextFile(configPath, originalSnapshot.text);
    } else if (await fileExists(configPath)) {
      await (0, import_promises3.rm)(configPath, { force: true });
    }
    throw error;
  }
  return getChannelsConfig(instance);
}

// src/routes/channels.ts
var app4 = new Hono2();
app4.get("/config", async (c) => {
  try {
    console.log("[channels] reading config snapshot");
    return c.json(await getChannelsConfig(ensureDefaultInstance()));
  } catch (error) {
    console.error("[channels:error] failed to read config snapshot");
    console.error(error instanceof Error ? error.stack || error.message : String(error));
    return c.json(
      { message: error instanceof Error ? error.message : String(error) },
      500
    );
  }
});
app4.get("/plugins", async (c) => {
  try {
    console.log("[channels] reading plugin status");
    return c.json(await getChannelPlugins(ensureDefaultInstance()));
  } catch (error) {
    console.error("[channels:error] failed to read plugin status");
    console.error(error instanceof Error ? error.stack || error.message : String(error));
    return c.json(
      { message: error instanceof Error ? error.message : String(error) },
      500
    );
  }
});
app4.post("/config", async (c) => {
  try {
    const body = await c.req.json().catch(() => ({ feishu: null }));
    console.log(`[channels] saving channel config payload keys=${Object.keys(body || {}).join(",")}`);
    return c.json(await saveChannelsConfig(ensureDefaultInstance(), body));
  } catch (error) {
    console.error("[channels:error] failed to save channel config");
    console.error(error instanceof Error ? error.stack || error.message : String(error));
    return c.json(
      { message: error instanceof Error ? error.message : String(error) },
      400
    );
  }
});
app4.post("/plugins/install", async (c) => {
  try {
    const body = await c.req.json().then((payload) => {
      const legacyChannelId = payload.channelId;
      if (!payload.channelKey && legacyChannelId) {
        return { channelKey: legacyChannelId };
      }
      return payload;
    }).catch(() => ({ channelKey: "feishu" }));
    console.log(`[channels] installing plugin for ${body.channelKey}`);
    return c.json(await installChannelPlugin(ensureDefaultInstance(), body));
  } catch (error) {
    console.error("[channels:error] failed to install channel plugin");
    console.error(error instanceof Error ? error.stack || error.message : String(error));
    return c.json(
      { message: error instanceof Error ? error.message : String(error) },
      400
    );
  }
});
var channels_default = app4;

// src/lib/models.ts
var import_fs10 = require("fs");
var import_promises4 = require("fs/promises");
var MODEL_CATALOG_CACHE_TTL_MS = 5 * 60 * 1e3;
var MODELS_CATALOG_COMMAND_TIMEOUT_MS = 3e4;
var MODELS_CONFIG_VALIDATE_TIMEOUT_MS = 1e4;
var catalogCache = /* @__PURE__ */ new Map();
var BUILTIN_PROVIDER_PRESETS = {
  anthropic: {
    baseUrl: "https://api.anthropic.com"
  },
  google: {
    baseUrl: "https://generativelanguage.googleapis.com/v1beta"
  },
  "minimax-cn": {
    baseUrl: "https://api.minimaxi.com/anthropic",
    api: "anthropic-messages",
    authHeader: true
  },
  minimax: {
    baseUrl: "https://api.minimax.io/anthropic",
    api: "anthropic-messages",
    authHeader: true
  },
  "kimi-coding": {
    baseUrl: "https://api.kimi.com/coding/",
    api: "anthropic-messages"
  },
  mistral: {
    baseUrl: "https://api.mistral.ai/v1",
    api: "openai-completions"
  },
  moonshot: {
    baseUrl: "https://api.moonshot.ai/v1",
    api: "openai-completions"
  },
  openai: {
    baseUrl: "https://api.openai.com/v1"
  },
  ollama: {
    baseUrl: "http://127.0.0.1:11434",
    api: "ollama"
  },
  openrouter: {
    baseUrl: "https://openrouter.ai/api/v1",
    api: "openai-completions"
  },
  together: {
    baseUrl: "https://api.together.xyz/v1",
    api: "openai-completions"
  },
  xai: {
    baseUrl: "https://api.x.ai/v1",
    api: "openai-completions"
  },
  zai: {
    baseUrl: "https://api.z.ai/api/paas/v4",
    api: "openai-completions"
  }
};
var PROVIDER_LABELS = {
  anthropic: "Anthropic",
  deepseek: "DeepSeek",
  google: "Google",
  "kimi-coding": "Kimi Coding",
  minimax: "MiniMax",
  "minimax-cn": "MiniMax CN",
  mistral: "Mistral",
  moonshot: "Moonshot",
  ollama: "Ollama",
  "opencode-go": "OpenCode Go",
  openai: "OpenAI",
  openrouter: "OpenRouter",
  together: "Together",
  xai: "xAI",
  zai: "Z.AI"
};
function humanizeProviderId(providerId) {
  return providerId.split(/[-_]/).filter(Boolean).map((segment) => {
    const lower = segment.toLowerCase();
    if (lower === "ai") {
      return "AI";
    }
    if (lower === "cn") {
      return "CN";
    }
    return segment.charAt(0).toUpperCase() + segment.slice(1);
  }).join(" ");
}
function providerDisplayName(providerId) {
  return PROVIDER_LABELS[providerId] || humanizeProviderId(providerId);
}
function editorSupportForProvider(providerId, providerType) {
  if (providerType === "custom-openai" || providerType === "ollama") {
    return { editorSupport: "full" };
  }
  if (getBuiltinProviderPreset(providerId)) {
    return { editorSupport: "full" };
  }
  return {
    editorSupport: "cli-only",
    editorReason: "\u8FD9\u4E2A\u5185\u5EFA provider \u6765\u81EA\u8F83\u65B0\u7684 OpenClaw \u80FD\u529B\u6216\u4E13\u7528 onboarding\uFF0Cmonitor \u6682\u672A\u786E\u8BA4\u5B83\u7684\u5B8C\u6574\u53EF\u89C6\u5316 schema\u3002"
  };
}
function getBuiltinProviderPreset(providerId) {
  const preset = BUILTIN_PROVIDER_PRESETS[providerId];
  if (!preset) {
    return null;
  }
  return {
    providerId,
    ...preset
  };
}
function listBuiltinProviderPresets() {
  return Object.entries(BUILTIN_PROVIDER_PRESETS).map(([providerId, preset]) => ({
    providerId,
    ...preset
  }));
}
function asObject2(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}
async function readConfigFile3(path) {
  return readLooseConfigFile(path);
}
function splitModelRef(modelRef) {
  const [providerId, ...rest] = modelRef.split("/");
  return {
    providerId,
    modelId: rest.join("/")
  };
}
function inferredProviderType(providerId, providerConfig) {
  if (getBuiltinProviderPreset(providerId)) {
    return providerId === "ollama" ? "ollama" : "builtin";
  }
  if (providerId === "ollama" || providerConfig?.api === "ollama") {
    return "ollama";
  }
  if (providerConfig?.baseUrl) {
    return "custom-openai";
  }
  return "builtin";
}
async function resolveOpenclawBinary3(instance) {
  return requireOpenclawBinary(instance);
}
async function tryResolveOpenclawBinary2(instance) {
  return resolveOpenclawBinary(instance);
}
async function runOpenclawCommand2(instance, args, options) {
  const bin = await resolveOpenclawBinary3(instance);
  return runCommandText([bin, ...args], {
    stdin: options?.stdin,
    timeoutMs: options?.timeoutMs,
    env: openclawEnv(instance),
    cwd: openclawSpawnCwd(instance)
  });
}
async function runOpenclawJsonCommand2(instance, args, options) {
  const result = await runOpenclawCommand2(instance, args, options);
  if (result.exitCode !== 0) {
    throw new Error(result.stderr || result.stdout || `openclaw ${args.join(" ")} failed`);
  }
  try {
    return parseJsonFromCommandOutput(result.stdout);
  } catch {
    throw new Error(`Invalid JSON from openclaw ${args.join(" ")}`);
  }
}
async function runOpenclawJsonCommandWithTimeout(instance, args, timeoutMs) {
  const commandPromise = runOpenclawJsonCommand2(instance, args);
  if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) {
    return commandPromise;
  }
  let timeoutId = null;
  try {
    return await Promise.race([
      commandPromise,
      new Promise((_, reject) => {
        timeoutId = setTimeout(() => {
          reject(new Error(`openclaw ${args.join(" ")} timed out after ${timeoutMs}ms`));
        }, timeoutMs);
      })
    ]);
  } finally {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
  }
}
async function getActiveConfigPath2(instance) {
  return activeConfigPath(instance);
}
function makeJsonArg2(value) {
  return JSON.stringify(value);
}
async function setConfigValue2(instance, path, value) {
  const result = await runOpenclawCommand2(instance, ["config", "set", path, makeJsonArg2(value), "--strict-json"]);
  if (result.exitCode !== 0) {
    throw new Error(result.stderr || result.stdout || `Failed to set ${path}`);
  }
}
async function unsetConfigValue(instance, path) {
  const result = await runOpenclawCommand2(instance, ["config", "unset", path]);
  if (result.exitCode !== 0) {
    throw new Error(result.stderr || result.stdout || `Failed to unset ${path}`);
  }
}
function buildConfiguredProviderEntry(providerId, providerConfig, catalogMap) {
  const providerType = inferredProviderType(providerId, providerConfig);
  const editorSupport = editorSupportForProvider(providerId, providerType);
  const providerApiKey = typeof providerConfig.apiKey === "string" ? providerConfig.apiKey : null;
  const models = Array.isArray(providerConfig.models) ? providerConfig.models : [];
  return {
    id: providerId,
    displayName: providerDisplayName(providerId),
    providerType,
    api: typeof providerConfig.api === "string" ? providerConfig.api : null,
    baseUrl: typeof providerConfig.baseUrl === "string" ? providerConfig.baseUrl : null,
    apiKeyConfigured: Boolean(providerApiKey),
    apiKeySource: providerApiKey ? "provider" : null,
    editorSupport: editorSupport.editorSupport,
    editorReason: editorSupport.editorReason,
    models: models.filter((model) => typeof model?.id === "string" && model.id.length > 0).map((model) => {
      const modelRef = `${providerId}/${model.id}`;
      const catalogItem = catalogMap.get(modelRef);
      return {
        modelRef,
        modelId: model.id,
        displayName: typeof model.name === "string" && model.name.trim() ? model.name.trim() : catalogItem?.name || model.id,
        available: Boolean(catalogItem?.available),
        local: Boolean(catalogItem?.local)
      };
    })
  };
}
function buildProviderCapabilities(models) {
  const providerTypeMap = /* @__PURE__ */ new Map();
  for (const preset of listBuiltinProviderPresets()) {
    providerTypeMap.set(preset.providerId, preset.providerId === "ollama" ? "ollama" : "builtin");
  }
  for (const model of models) {
    if (!providerTypeMap.has(model.providerId)) {
      providerTypeMap.set(model.providerId, model.providerType);
    }
  }
  return Array.from(providerTypeMap.entries()).sort((a, b) => providerDisplayName(a[0]).localeCompare(providerDisplayName(b[0]))).map(([providerId, providerType]) => {
    const preset = getBuiltinProviderPreset(providerId);
    const editorSupport = editorSupportForProvider(providerId, providerType);
    return {
      providerId,
      displayName: providerDisplayName(providerId),
      providerType,
      editorSupport: editorSupport.editorSupport,
      editorReason: editorSupport.editorReason,
      baseUrl: preset?.baseUrl,
      api: preset?.api,
      authHeader: preset?.authHeader
    };
  });
}
async function getModelsCatalog(instance) {
  if (!await tryResolveOpenclawBinary2(instance)) {
    catalogCache.delete(instance.id);
    return {
      count: 0,
      models: [],
      providerPresets: listBuiltinProviderPresets(),
      providerCapabilities: buildProviderCapabilities([])
    };
  }
  const now = Date.now();
  const cached = catalogCache.get(instance.id);
  if (cached && now - cached.fetchedAt < MODEL_CATALOG_CACHE_TTL_MS) {
    return cached.value;
  }
  const raw2 = await runOpenclawJsonCommand2(
    instance,
    ["models", "list", "--all", "--json"],
    { timeoutMs: MODELS_CATALOG_COMMAND_TIMEOUT_MS }
  );
  const value = {
    count: typeof raw2.count === "number" ? raw2.count : 0,
    models: Array.isArray(raw2.models) ? raw2.models.flatMap((model) => {
      const key = typeof model.key === "string" ? model.key : "";
      if (!key.includes("/")) {
        return [];
      }
      const { providerId, modelId } = splitModelRef(key);
      const item = {
        key,
        name: typeof model.name === "string" ? model.name : modelId,
        local: Boolean(model.local),
        available: Boolean(model.available),
        missing: Boolean(model.missing),
        providerId,
        providerType: inferredProviderType(providerId, null),
        modelId
      };
      if (typeof model.input === "string") {
        item.input = model.input;
      }
      if (typeof model.contextWindow === "number") {
        item.contextWindow = model.contextWindow;
      }
      return [item];
    }) : [],
    providerPresets: listBuiltinProviderPresets(),
    providerCapabilities: []
  };
  value.providerCapabilities = buildProviderCapabilities(value.models);
  catalogCache.set(instance.id, {
    fetchedAt: now,
    value
  });
  return value;
}
async function getModelsConfig(instance) {
  const binaryPath = await tryResolveOpenclawBinary2(instance);
  const activeConfigPath3 = await getActiveConfigPath2(instance);
  const configExists = (0, import_fs10.existsSync)(activeConfigPath3);
  const config = await readConfigFile3(activeConfigPath3);
  let validation = {
    valid: true,
    path: activeConfigPath3
  };
  if (binaryPath && configExists) {
    try {
      validation = await runOpenclawJsonCommandWithTimeout(
        instance,
        ["config", "validate", "--json"],
        MODELS_CONFIG_VALIDATE_TIMEOUT_MS
      );
    } catch (error) {
      console.warn("[models] skipped blocking config validation for config snapshot:", error);
    }
  }
  const catalogMap = /* @__PURE__ */ new Map();
  const providerConfig = asObject2(asObject2(config.models).providers);
  const providers = {};
  for (const [providerId, value] of Object.entries(providerConfig)) {
    providers[providerId] = asObject2(value);
  }
  const configuredProviders = Object.entries(providers).map(
    ([providerId, provider]) => buildConfiguredProviderEntry(providerId, provider, catalogMap)
  );
  return {
    configPath: validation.path || activeConfigPath3,
    configExists,
    validation: {
      valid: Boolean(validation.valid),
      message: Array.isArray(validation.errors) && validation.errors.length > 0 ? validation.errors.join("; ") : typeof validation.error === "string" && validation.error.length > 0 ? validation.error : void 0
    },
    configuredProviders
  };
}
function normalizeProviderInput(provider) {
  const providerId = provider.providerId.trim();
  const api = typeof provider.api === "string" ? provider.api.trim() : void 0;
  const apiKey = typeof provider.apiKey === "string" ? provider.apiKey.trim() : provider.apiKey;
  const baseUrl = provider.baseUrl?.trim();
  const modelIds = Array.from(
    new Set(
      Array.isArray(provider.modelIds) ? provider.modelIds.map((modelId) => modelId.trim()).filter((modelId) => modelId.length > 0) : []
    )
  );
  if (!providerId) {
    throw new Error("providerId is required");
  }
  if (!["builtin", "custom-openai", "ollama"].includes(provider.providerType)) {
    throw new Error("providerType is invalid");
  }
  if (provider.providerType === "builtin" && !getBuiltinProviderPreset(providerId)) {
    throw new Error(
      `\u5185\u5EFA provider ${providerId} \u5F53\u524D\u4E0D\u5728 monitor \u5DF2\u786E\u8BA4\u652F\u6301\u7684\u53EF\u89C6\u5316\u8303\u56F4\u5185\uFF0C\u8BF7\u6539\u7528 OpenClaw \u5B98\u65B9 onboarding \u6216 CLI \u7BA1\u7406`
    );
  }
  if (modelIds.length === 0) {
    throw new Error(`provider ${providerId} must include at least one modelId`);
  }
  return {
    providerId,
    providerType: provider.providerType,
    api,
    apiKey,
    baseUrl: baseUrl || "",
    modelIds
  };
}
function catalogLookupMap(catalog) {
  return new Map(catalog.models.map((model) => [model.key, model]));
}
function providerModelRef(providerId, modelId) {
  return `${providerId}/${modelId}`;
}
function providerApiForProviderInput(provider, currentProvider, preset) {
  if (typeof provider.api === "string" && provider.api.trim()) {
    return provider.api.trim();
  }
  if (typeof currentProvider?.api === "string" && currentProvider.api.trim()) {
    return currentProvider.api;
  }
  if (typeof preset?.api === "string" && preset.api.trim()) {
    return preset.api;
  }
  if (provider.providerType === "ollama") {
    return "ollama";
  }
  if (provider.providerType === "custom-openai") {
    return "openai-completions";
  }
  return void 0;
}
function displayNameForProviderModel(providerId, modelId, catalogMap) {
  return catalogMap.get(providerModelRef(providerId, modelId))?.name || modelId;
}
function providerModelRefsFromProviders(providers) {
  const refs = /* @__PURE__ */ new Set();
  for (const [providerId, provider] of Object.entries(providers)) {
    const models = Array.isArray(provider.models) ? provider.models : [];
    for (const model of models) {
      if (typeof model?.id === "string" && model.id.trim()) {
        refs.add(providerModelRef(providerId, model.id.trim()));
      }
    }
  }
  return refs;
}
function buildSyncedAllowlist(currentAllowlist, currentProviders, nextProviders) {
  const previousProviderModelRefs = providerModelRefsFromProviders(currentProviders);
  const nextProviderModelRefs = providerModelRefsFromProviders(nextProviders);
  const nextAllowlist = {};
  for (const [modelRef, value] of Object.entries(currentAllowlist)) {
    if (previousProviderModelRefs.has(modelRef) && !nextProviderModelRefs.has(modelRef)) {
      continue;
    }
    nextAllowlist[modelRef] = asObject2(value);
  }
  for (const modelRef of nextProviderModelRefs) {
    nextAllowlist[modelRef] = asObject2(nextAllowlist[modelRef]);
  }
  return nextAllowlist;
}
async function saveModelsConfig(instance, payload) {
  console.log(`[models] saveModelsConfig start for instance=${instance.id}`);
  if (!await tryResolveOpenclawBinary2(instance)) {
    throw new Error("OpenClaw is not installed yet. Install it before configuring models.");
  }
  if (!Array.isArray(payload.providers)) {
    throw new Error("providers must be an array");
  }
  const normalizedProviders = payload.providers.map(normalizeProviderInput);
  console.log(`[models] normalized providers=${normalizedProviders.length}`);
  const uniqueProviderIds = /* @__PURE__ */ new Set();
  for (const provider of normalizedProviders) {
    if (uniqueProviderIds.has(provider.providerId)) {
      throw new Error(`Duplicate provider entry: ${provider.providerId}`);
    }
    uniqueProviderIds.add(provider.providerId);
  }
  const configPath = await getActiveConfigPath2(instance);
  console.log(`[models] target config path=${configPath}`);
  const currentConfig = await readConfigFile3(configPath);
  const currentProvidersRaw = asObject2(asObject2(currentConfig.models).providers);
  const currentDefaultsRaw = asObject2(asObject2(currentConfig.agents).defaults);
  const currentAllowlist = asObject2(currentDefaultsRaw.models);
  const currentProviders = {};
  for (const [providerId, value] of Object.entries(currentProvidersRaw)) {
    currentProviders[providerId] = asObject2(value);
  }
  const catalogMap = catalogLookupMap(await getModelsCatalog(instance));
  const nextProviders = {};
  for (const provider of normalizedProviders) {
    const currentProvider = currentProviders[provider.providerId];
    const preset = getBuiltinProviderPreset(provider.providerId);
    const nextProvider = currentProvider ? { ...currentProvider } : {};
    const api = providerApiForProviderInput(provider, currentProvider, preset);
    const effectiveBaseUrl = provider.baseUrl || (typeof currentProvider?.baseUrl === "string" ? currentProvider.baseUrl.trim() : "") || preset?.baseUrl || "";
    if (!effectiveBaseUrl) {
      throw new Error(
        `provider ${provider.providerId} \u7F3A\u5C11 baseUrl\uFF1B\u8BF7\u624B\u52A8\u586B\u5199\uFF0C\u6216\u5148\u5728 monitor \u5185\u5EFA\u9884\u8BBE\u4E2D\u8865\u5145\u5B83`
      );
    }
    if (api) {
      nextProvider.api = api;
    }
    nextProvider.baseUrl = effectiveBaseUrl;
    if (typeof currentProvider?.authHeader === "boolean") {
      nextProvider.authHeader = currentProvider.authHeader;
    } else if (typeof preset?.authHeader === "boolean") {
      nextProvider.authHeader = preset.authHeader;
    }
    if (typeof provider.apiKey === "string") {
      if (provider.providerType === "ollama") {
        nextProvider.apiKey = provider.apiKey || "ollama-local";
      } else if (provider.apiKey) {
        nextProvider.apiKey = provider.apiKey;
      }
    } else if (typeof currentProvider?.apiKey === "string") {
      nextProvider.apiKey = currentProvider.apiKey;
    }
    nextProvider.models = provider.modelIds.map((modelId) => ({
      id: modelId,
      name: displayNameForProviderModel(provider.providerId, modelId, catalogMap)
    }));
    nextProviders[provider.providerId] = nextProvider;
  }
  const nextAllowlist = buildSyncedAllowlist(currentAllowlist, currentProviders, nextProviders);
  console.log("[models] next providers summary");
  console.log(JSON.stringify(
    Object.fromEntries(
      Object.entries(nextProviders).map(([providerId, provider]) => [
        providerId,
        {
          api: provider.api ?? null,
          baseUrl: provider.baseUrl ?? null,
          authHeader: typeof provider.authHeader === "boolean" ? provider.authHeader : null,
          apiKeyConfigured: typeof provider.apiKey === "string" && provider.apiKey.length > 0,
          modelIds: Array.isArray(provider.models) ? provider.models.filter((model) => typeof model?.id === "string").map((model) => model.id) : []
        }
      ])
    ),
    null,
    2
  ));
  const originalSnapshot = {
    exists: await fileExists(configPath),
    text: await readTextFileIfExists(configPath) || ""
  };
  try {
    console.log("[models] writing models.providers");
    if (Object.keys(nextProviders).length > 0) {
      await setConfigValue2(instance, "models.providers", nextProviders);
    } else {
      await unsetConfigValue(instance, "models.providers").catch(() => void 0);
    }
    if (Object.keys(nextAllowlist).length > 0) {
      console.log("[models] writing agents.defaults.models");
      await setConfigValue2(instance, "agents.defaults.models", nextAllowlist);
    } else {
      console.log("[models] clearing agents.defaults.models");
      await unsetConfigValue(instance, "agents.defaults.models").catch(() => void 0);
    }
    console.log("[models] validating config");
    const validation = await runOpenclawJsonCommand2(
      instance,
      ["config", "validate", "--json"]
    );
    if (!validation.valid) {
      throw new Error(
        Array.isArray(validation.errors) && validation.errors.length > 0 ? validation.errors.join("; ") : "Config validation failed"
      );
    }
  } catch (error) {
    console.error("[models:error] saveModelsConfig failed, rolling back config file");
    console.error(error instanceof Error ? error.stack || error.message : String(error));
    if (originalSnapshot.exists) {
      await writeTextFile(configPath, originalSnapshot.text);
    } else if (await fileExists(configPath)) {
      await (0, import_promises4.rm)(configPath, { force: true });
    }
    throw error;
  }
  console.log("[models] saveModelsConfig completed");
  return getModelsConfig(instance);
}

// src/routes/models.ts
var app5 = new Hono2();
app5.get("/config", async (c) => {
  try {
    console.log("[models] reading config snapshot");
    return c.json(await getModelsConfig(ensureDefaultInstance()));
  } catch (error) {
    console.error("[models:error] failed to read config snapshot");
    console.error(error instanceof Error ? error.stack || error.message : String(error));
    return c.json(
      { message: error instanceof Error ? error.message : String(error) },
      500
    );
  }
});
app5.get("/catalog", async (c) => {
  try {
    console.log("[models] reading models catalog");
    return c.json(await getModelsCatalog(ensureDefaultInstance()));
  } catch (error) {
    console.error("[models:error] failed to read models catalog");
    console.error(error instanceof Error ? error.stack || error.message : String(error));
    return c.json(
      { message: error instanceof Error ? error.message : String(error) },
      500
    );
  }
});
app5.post("/config", async (c) => {
  try {
    const body = await c.req.json().catch(() => ({ providers: [] }));
    console.log(`[models] saving config with ${body.providers.length} providers`);
    return c.json(await saveModelsConfig(ensureDefaultInstance(), body));
  } catch (error) {
    console.error("[models:error] failed to save models config");
    console.error(error instanceof Error ? error.stack || error.message : String(error));
    return c.json(
      { message: error instanceof Error ? error.message : String(error) },
      400
    );
  }
});
var models_default = app5;

// src/routes/status.ts
var app6 = new Hono2();
app6.get("/", async (c) => {
  return c.json(await getInstanceStatus(ensureDefaultInstance(), c));
});
var status_default = app6;

// src/index.ts
var basePath = MONITOR_BASE_PATH;
var apiBase = `${basePath}/api`;
var assetsBase = `${basePath}/assets`;
var moduleDir = __dirname;
var staticDir = process.env.STATIC_DIR || (0, import_path5.resolve)(moduleDir, "../../web/dist");
var port = parseInt(process.env.PORT || "3000", 10);
function requestUrlFromIncoming(incoming) {
  const host = incoming.headers.host || `127.0.0.1:${port}`;
  const protocol = "https" in incoming.socket && incoming.socket.encrypted ? "https" : "http";
  return `${protocol}://${host}${incoming.url || "/"}`;
}
function buildRequestFromIncoming(incoming) {
  const headers = new Headers();
  for (const [key, value] of Object.entries(incoming.headers)) {
    if (Array.isArray(value)) {
      for (const entry of value) {
        headers.append(key, entry);
      }
      continue;
    }
    if (typeof value === "string") {
      headers.set(key, value);
    }
  }
  return new Request(requestUrlFromIncoming(incoming), {
    method: incoming.method || "GET",
    headers
  });
}
async function writeResponseToSocket(socket, response) {
  const body = response.body ? Buffer.from(await response.arrayBuffer()) : Buffer.alloc(0);
  const headers = new Headers(response.headers);
  headers.set("Connection", "close");
  headers.set("Content-Length", String(body.length));
  const statusLine = `HTTP/1.1 ${response.status} ${response.statusText || "Error"}`;
  const headerLines = Array.from(headers.entries()).map(([key, value]) => `${key}: ${value}`);
  socket.write(`${statusLine}\r
${headerLines.join("\r\n")}\r
\r
`);
  socket.end(body);
}
async function bootstrap() {
  const app7 = new Hono2();
  const isDev = isLikelyDevEnvironment();
  const useSystemOpenclaw = shouldUseSystemOpenclaw(DEFAULT_INSTANCE_ID);
  console.log(`[monitor] Environment: ${isDev ? "development" : "production"}`);
  console.log(`[monitor] OpenClaw mode: ${useSystemOpenclaw ? "system (global)" : "managed (isolated)"}`);
  if (useSystemOpenclaw) {
    console.log(`[monitor] System OpenClaw config: ~/.openclaw/openclaw.json`);
    console.log(`[monitor] Note: Monitor will use your global OpenClaw installation`);
  } else {
    console.log(`[monitor] Managed OpenClaw config: DATA_ROOT/home/.openclaw/openclaw.json`);
  }
  if (isDev && useSystemOpenclaw) {
    await ensureDevModeConfig();
  }
  startRuntimeReconciler();
  app7.use(`${apiBase}/*`, cors());
  app7.use(`${apiBase}/*`, async (c, next) => {
    const startedAt = Date.now();
    console.log(`[api] -> ${c.req.method} ${c.req.path}`);
    await next();
    console.log(`[api] <- ${c.req.method} ${c.req.path} ${c.res.status} ${Date.now() - startedAt}ms`);
  });
  app7.onError((error, c) => {
    console.error(`[api:error] ${c.req.method} ${c.req.path}`);
    console.error(error instanceof Error ? error.stack || error.message : String(error));
    return c.json(
      { message: error instanceof Error ? error.message : String(error) },
      500
    );
  });
  app7.route(`${apiBase}/status`, status_default);
  app7.route(`${apiBase}/install`, install_default);
  app7.route(`${apiBase}/gateway`, gateway_default);
  app7.route(`${apiBase}/instances`, instances_default);
  app7.route(`${apiBase}/models`, models_default);
  app7.route(`${apiBase}/channels`, channels_default);
  app7.get(`${apiBase}/health`, (c) => {
    return c.json({ status: "ok", port: process.env.PORT || 3e3 });
  });
  app7.get(`${assetsBase}/*`, async (c) => {
    const requestPath = basePath !== "" && c.req.path.startsWith(basePath) ? c.req.path.slice(basePath.length) : c.req.path;
    const filePath = (0, import_path5.join)(staticDir, requestPath);
    if (!await fileExists(filePath)) {
      return c.notFound();
    }
    const file = await readStaticFile(filePath);
    return new Response(file.body, {
      headers: {
        "Content-Length": String(file.size),
        "Content-Type": file.contentType
      }
    });
  });
  const indexHandler = async (c) => {
    const indexPath = (0, import_path5.join)(staticDir, "index.html");
    if (!await fileExists(indexPath)) {
      return c.text("index.html not found. Run 'pnpm build:web' first.", 404);
    }
    const file = await readStaticFile(indexPath);
    return new Response(file.body, {
      headers: {
        "Content-Length": String(file.size),
        "Content-Type": "text/html; charset=utf-8"
      }
    });
  };
  if (basePath === "") {
    app7.get("*", indexHandler);
  } else {
    app7.get(basePath, indexHandler);
    app7.get(`${basePath}/`, indexHandler);
    app7.get(`${basePath}/*`, indexHandler);
  }
  const server = createAdaptorServer({
    fetch: async (request, env) => {
      const clientIp = env.incoming.socket.remoteAddress;
      if (!shouldAllowClientIp(clientIp)) {
        return accessDeniedResponse(clientIp);
      }
      const authResult = await authenticateRequest(request);
      if (!authResult.ok) {
        return authResult.response;
      }
      const proxiedHttp = await maybeProxyHttpRequest(request, clientIp);
      if (proxiedHttp !== null) {
        return proxiedHttp;
      }
      return app7.fetch(request);
    }
  });
  server.on("upgrade", async (incoming, socket, head) => {
    try {
      const request = buildRequestFromIncoming(incoming);
      const clientIp = incoming.socket.remoteAddress;
      if (!shouldAllowClientIp(clientIp)) {
        await writeResponseToSocket(socket, accessDeniedResponse(clientIp));
        return;
      }
      const authResult = await authenticateRequest(request);
      if (!authResult.ok) {
        await writeResponseToSocket(socket, authResult.response);
        return;
      }
      const handled = await maybeHandleProxyWebSocketUpgrade(
        request,
        incoming,
        socket,
        head,
        clientIp
      );
      if (!handled) {
        socket.destroy();
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      await writeResponseToSocket(socket, new Response(message, { status: 500 }));
    }
  });
  server.on("error", (error) => {
    console.error("[monitor] server listen failed");
    console.error(error instanceof Error ? error.stack || error.message : String(error));
    process.exit(1);
  });
  server.listen(port, () => {
    console.log(`Server is running on http://localhost:${port}`);
    console.log(`Serving static files from: ${staticDir}`);
    console.log(`Base path: ${basePath || "/"}`);
    console.log(`fnOS auth enabled: ${FN_AUTH_ENABLED ? "yes" : "no"}`);
    console.log(`auth cookies: ${FN_AUTH_COOKIE_NAME}, ${FN_AUTH_ENTRY_COOKIE_NAME}`);
    console.log(`fnOS same-origin guard: ${FN_AUTH_REQUIRE_SAME_ORIGIN ? "yes" : "no"}`);
  });
}
void bootstrap().catch((error) => {
  console.error("[monitor] bootstrap failed");
  console.error(error instanceof Error ? error.stack || error.message : String(error));
  process.exit(1);
});
//# sourceMappingURL=index.cjs.map
