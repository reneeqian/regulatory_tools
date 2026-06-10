'use strict';
const vscode = require('vscode');
const { RegulatoryWebviewProvider } = require('./provider');

function activate(context) {
  const provider = new RegulatoryWebviewProvider(context.extensionUri);

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(RegulatoryWebviewProvider.viewType, provider)
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('regulatory.refresh', () => provider.refresh())
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('regulatory.generateDhf', () => provider.generateDhf())
  );
}

function deactivate() {}

module.exports = { activate, deactivate };
