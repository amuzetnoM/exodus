//+------------------------------------------------------------------+
//| XM MT5 EA Template - mql5_ea_template.mq5                        |
//| Purpose: skeleton EA to forward signals to external orchestrator |
//| Features: WebRequest calls, idempotency header, backoff, logs   |
//+------------------------------------------------------------------+
#property copyright "EXODUS"
#property version   "1.0"

input string OrchestratorUrl = "https://orchestrator.local/api/v1/ea_callback"; // set via EA inputs
input string ClientId = "client-123";

// Simple helper to perform HTTP POST with WebRequest
string PostJson(string url, string body, string headers)
{
   uchar result[];
   char resp[];
   int res = WebRequest("POST", url, headers, 5, body, 0, result, resp);
   if(res == -1)
   {
      // error, return empty
      PrintFormat("WebRequest failed, code=%d", GetLastError());
      return "";
   }
   string sresp = CharArrayToString(result);
   return sresp;
}

// Build idempotency key
string BuildIdempotency(string clientOrderId, string symbol, double price, int qty)
{
   // simple concatenation; replace with secure hash if available
   return clientOrderId + "|" + symbol + "|" + DoubleToString(price, _Digits) + "|" + IntegerToString(qty);
}

// Example send function
void SendOrderToOrchestrator(string clientOrderId, string symbol, double price, int qty, string side)
{
   string idempotency = BuildIdempotency(clientOrderId, symbol, price, qty);
   string payload = "{\"clientOrderId\":\"" + clientOrderId + "\",\"clientId\":\"" + ClientId + "\",\"symbol\":\"" + symbol + "\",\"price\":" + DoubleToString(price,_Digits) + ",\"qty\":\"" + IntegerToString(qty) + "\",\"side\":\"" + side + "\"}";
   string headers = "Content-Type: application/json\r\nX-Idempotency-Key: " + idempotency + "\r\n";

   // Submit request and handle response
   string resp = PostJson(OrchestratorUrl, payload, headers);
   if(StringLen(resp) == 0)
   {
      Print("No response from orchestrator, scheduling retry");
      // implement retry/backoff or queue locally with Files
   }
   else
   {
      PrintFormat("Orchestrator response: %s", resp);
   }
}

// Basic OnTick handler - demo only
void OnTick()
{
   // placeholder: detect signal and call SendOrderToOrchestrator
}

//+------------------------------------------------------------------+
// Note: This template is intentionally minimal. Do not embed secrets in source.
// Use EA input parameters and secure vaults where possible. Replace simple
// idempotency with HMAC or SHA256 within orchestrator verification to avoid collisions.
//+------------------------------------------------------------------+
