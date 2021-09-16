const HtmlWebpackPlugin = require('html-webpack-plugin');
const InlineChunkHtmlPlugin = require('react-dev-utils/InlineChunkHtmlPlugin');

module.exports = function override(config, env) {
  if (env === 'production') {
    config.plugins.push(new InlineChunkHtmlPlugin(HtmlWebpackPlugin, [/.+[.]js/]))
  }
  return config
}