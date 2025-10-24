//+------------------------------------------------------------------+
//|                                           EXODUS MT5 Bridge EA    |
//|                                  PRODUCTION - HANDLES REAL FUNDS |
//|                                     Connects MT5 to EXODUS Platform |
//+------------------------------------------------------------------+
#property copyright "EXODUS Trading Platform"
#property link      "https://github.com/amuzetnoM/exodus"
#property version   "1.00"
#property strict

// EXODUS Orchestrator Configuration
input string OrchestratorURL = "http://localhost:8000";  // EXODUS API URL
input int    UpdateIntervalSeconds = 5;                   // Position update interval
input int    MagicNumber = 123456;                         // EA Magic Number
input bool   EnableWebRequest = true;                      // Enable WebRequest

// Global Variables
datetime lastUpdateTime = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("========================================");
    Print("EXODUS MT5 Bridge EA - PRODUCTION MODE");
    Print("========================================");
    Print("Orchestrator URL: ", OrchestratorURL);
    Print("Account: ", AccountInfoInteger(ACCOUNT_LOGIN));
    Print("Server: ", AccountInfoString(ACCOUNT_SERVER));
    Print("========================================");
    
    // Verify WebRequest is enabled for our orchestrator
    if(EnableWebRequest)
    {
        Print("WebRequest is enabled");
        Print("Allowed URLs must include: ", OrchestratorURL);
    }
    else
    {
        Print("WARNING: WebRequest is disabled!");
        return(INIT_FAILED);
    }
    
    // Send initial connection status
    SendHeartbeat();
    
    // Send current positions immediately
    SendPositionsUpdate();
    
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    Print("EXODUS MT5 Bridge EA shutting down. Reason: ", reason);
}

//+------------------------------------------------------------------+
//| Expert tick function                                              |
//+------------------------------------------------------------------+
void OnTick()
{
    // Update positions at regular intervals
    if(TimeCurrent() - lastUpdateTime >= UpdateIntervalSeconds)
    {
        SendPositionsUpdate();
        SendAccountUpdate();
        lastUpdateTime = TimeCurrent();
    }
}

//+------------------------------------------------------------------+
//| Send heartbeat to orchestrator                                    |
//+------------------------------------------------------------------+
void SendHeartbeat()
{
    string url = OrchestratorURL + "/api/mt5/heartbeat";
    string headers = "Content-Type: application/json\r\n";
    
    string json = StringFormat(
        "{\"account\":\"%d\",\"server\":\"%s\",\"timestamp\":\"%s\",\"status\":\"connected\"}",
        AccountInfoInteger(ACCOUNT_LOGIN),
        AccountInfoString(ACCOUNT_SERVER),
        TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS)
    );
    
    char post_data[];
    char result[];
    string result_headers;
    
    ArrayResize(post_data, StringToCharArray(json, post_data, 0, WHOLE_ARRAY) - 1);
    
    int res = WebRequest(
        "POST",
        url,
        headers,
        5000,
        post_data,
        result,
        result_headers
    );
    
    if(res == 200)
    {
        Print("✅ Heartbeat sent successfully");
    }
    else
    {
        Print("❌ Heartbeat failed. Code: ", res);
        Print("   Make sure ", url, " is in Allowed URLs");
    }
}

//+------------------------------------------------------------------+
//| Send positions update to orchestrator                             |
//+------------------------------------------------------------------+
void SendPositionsUpdate()
{
    string url = OrchestratorURL + "/api/mt5/positions";
    string headers = "Content-Type: application/json\r\n";
    
    // Build JSON array of positions
    string positions_json = "[";
    int total = PositionsTotal();
    
    Print("📊 Found ", total, " active positions");
    
    for(int i = 0; i < total; i++)
    {
        ulong ticket = PositionGetTicket(i);
        if(ticket > 0)
        {
            string symbol = PositionGetString(POSITION_SYMBOL);
            double volume = PositionGetDouble(POSITION_VOLUME);
            double price_open = PositionGetDouble(POSITION_PRICE_OPEN);
            double price_current = PositionGetDouble(POSITION_PRICE_CURRENT);
            double profit = PositionGetDouble(POSITION_PROFIT);
            double sl = PositionGetDouble(POSITION_SL);
            double tp = PositionGetDouble(POSITION_TP);
            ENUM_POSITION_TYPE type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
            datetime time_open = (datetime)PositionGetInteger(POSITION_TIME);
            string comment = PositionGetString(POSITION_COMMENT);
            
            string type_str = (type == POSITION_TYPE_BUY) ? "buy" : "sell";
            
            if(i > 0) positions_json += ",";
            
            positions_json += StringFormat(
                "{\"ticket\":%I64u,\"symbol\":\"%s\",\"type\":\"%s\",\"volume\":%.2f,"
                "\"price_open\":%.5f,\"price_current\":%.5f,\"profit\":%.2f,"
                "\"sl\":%.5f,\"tp\":%.5f,\"time_open\":\"%s\",\"comment\":\"%s\"}",
                ticket,
                symbol,
                type_str,
                volume,
                price_open,
                price_current,
                profit,
                sl,
                tp,
                TimeToString(time_open, TIME_DATE|TIME_SECONDS),
                comment
            );
            
            // Print position details
            Print("   Position #", ticket, ": ", symbol, " ", type_str, " ",
                  volume, " lots @ ", price_open, " | P&L: $", profit);
        }
    }
    
    positions_json += "]";
    
    // Send to orchestrator
    char post_data[];
    char result[];
    string result_headers;
    
    ArrayResize(post_data, StringToCharArray(positions_json, post_data, 0, WHOLE_ARRAY) - 1);
    
    int res = WebRequest(
        "POST",
        url,
        headers,
        5000,
        post_data,
        result,
        result_headers
    );
    
    if(res == 200)
    {
        Print("✅ Positions update sent successfully");
    }
    else
    {
        Print("❌ Positions update failed. Code: ", res);
    }
}

//+------------------------------------------------------------------+
//| Send account update to orchestrator                               |
//+------------------------------------------------------------------+
void SendAccountUpdate()
{
    string url = OrchestratorURL + "/api/mt5/account";
    string headers = "Content-Type: application/json\r\n";
    
    string json = StringFormat(
        "{\"account\":\"%d\",\"server\":\"%s\","
        "\"balance\":%.2f,\"equity\":%.2f,\"margin\":%.2f,\"free_margin\":%.2f,"
        "\"margin_level\":%.2f,\"profit\":%.2f,\"timestamp\":\"%s\"}",
        AccountInfoInteger(ACCOUNT_LOGIN),
        AccountInfoString(ACCOUNT_SERVER),
        AccountInfoDouble(ACCOUNT_BALANCE),
        AccountInfoDouble(ACCOUNT_EQUITY),
        AccountInfoDouble(ACCOUNT_MARGIN),
        AccountInfoDouble(ACCOUNT_MARGIN_FREE),
        AccountInfoDouble(ACCOUNT_MARGIN_LEVEL),
        AccountInfoDouble(ACCOUNT_PROFIT),
        TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS)
    );
    
    char post_data[];
    char result[];
    string result_headers;
    
    ArrayResize(post_data, StringToCharArray(json, post_data, 0, WHOLE_ARRAY) - 1);
    
    int res = WebRequest(
        "POST",
        url,
        headers,
        5000,
        post_data,
        result,
        result_headers
    );
    
    if(res == 200)
    {
        Print("✅ Account update sent");
    }
}
//+------------------------------------------------------------------+
