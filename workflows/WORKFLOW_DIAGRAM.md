# Scholarship Processing Workflow Diagrams

## Overall System Architecture

```mermaid
graph TB
    subgraph "Input Data"
        SF[Scholarship Folder]
        WAI[WAI Application Folders]
        CONFIG[agents.json]
        CRITERIA[Criteria Folder]
    end
    
    subgraph "Workflow Orchestration"
        WF[ScholarshipProcessingWorkflow]
    end
    
    subgraph "Processing Agents"
        ATT[Attachment Agent<br/>PII Redaction]
        APP[Application Agent<br/>Info Extraction]
        REC[Recommendation Agent<br/>Letter Analysis]
        ACA[Academic Agent<br/>Profile Analysis]
        ESS[Essay Agent<br/>Essay Analysis]
        SUM[Summary Agent<br/>Report Generation]
    end
    
    subgraph "Output Data"
        ATTOUT[Redacted Text Files]
        APPOUT[Application JSON]
        RECOUT[Recommendation JSON]
        ACAOUT[Academic JSON]
        ESSOUT[Essay JSON]
        CSV[Summary CSV]
        STATS[Statistics Report]
    end
    
    SF --> WF
    WAI --> WF
    CONFIG --> WF
    CRITERIA --> WF
    
    WF --> ATT
    WF --> APP
    WF --> REC
    WF --> ACA
    WF --> ESS
    WF --> SUM
    
    ATT --> ATTOUT
    APP --> APPOUT
    REC --> RECOUT
    ACA --> ACAOUT
    ESS --> ESSOUT
    SUM --> CSV
    SUM --> STATS
    
    style WF fill:#4A90E2,stroke:#2E5C8A,color:#fff
    style ATT fill:#50C878,stroke:#2E7D4E,color:#fff
    style APP fill:#50C878,stroke:#2E7D4E,color:#fff
    style REC fill:#50C878,stroke:#2E7D4E,color:#fff
    style ACA fill:#50C878,stroke:#2E7D4E,color:#fff
    style ESS fill:#50C878,stroke:#2E7D4E,color:#fff
    style SUM fill:#50C878,stroke:#2E7D4E,color:#fff
```

## Parallel Processing Architecture

```mermaid
graph TB
    subgraph "Stage 1: Application"
        START[Start Processing] --> APP[Application Agent<br/>Info Extraction]
    end
    
    subgraph "Stage 2: Attachments"
        APP --> ATT[Attachment Agent<br/>PII Redaction]
    end
    
    subgraph "Stage 3: Parallel Analysis"
        ATT --> FORK{Fork to<br/>3 Threads}
        
        FORK --> T1[Thread 1]
        FORK --> T2[Thread 2]
        FORK --> T3[Thread 3]
        
        T1 --> REC[Recommendation Agent<br/>Letter Analysis]
        T2 --> ACA[Academic Agent<br/>Profile Analysis]
        T3 --> ESS[Essay Agent<br/>Essay Analysis]
        
        REC --> JOIN[Join Results]
        ACA --> JOIN
        ESS --> JOIN
    end
    
    subgraph "Phase 3: Summary Generation"
        JOIN --> SUM[Summary Agent<br/>CSV & Statistics]
        SUM --> END[Complete]
    end
    
    style START fill:#4A90E2,stroke:#2E5C8A,color:#fff
    style END fill:#4A90E2,stroke:#2E5C8A,color:#fff
    style ATT fill:#50C878,stroke:#2E7D4E,color:#fff
    style APP fill:#50C878,stroke:#2E7D4E,color:#fff
    style FORK fill:#FFD700,stroke:#B8860B,color:#000
    style JOIN fill:#FFD700,stroke:#B8860B,color:#000
    style T1 fill:#9370DB,stroke:#4B0082,color:#fff
    style T2 fill:#9370DB,stroke:#4B0082,color:#fff
    style T3 fill:#9370DB,stroke:#4B0082,color:#fff
    style REC fill:#50C878,stroke:#2E7D4E,color:#fff
    style ACA fill:#50C878,stroke:#2E7D4E,color:#fff
    style ESS fill:#50C878,stroke:#2E7D4E,color:#fff
    style SUM fill:#50C878,stroke:#2E7D4E,color:#fff
```

## Sequential Processing Flow

```mermaid
sequenceDiagram
    participant User
    participant Workflow
    participant AttAgent as Attachment Agent
    participant AppAgent as Application Agent
    participant RecAgent as Recommendation Agent
    participant AcaAgent as Academic Agent
    participant EssAgent as Essay Agent
    participant SumAgent as Summary Agent
    
    User->>Workflow: process_applicant(wai_number)
    
    Note over Workflow: Stage 1: Attachments
    Workflow->>AttAgent: process_attachments(wai_number)
    AttAgent->>AttAgent: Scan for attachments
    AttAgent->>AttAgent: Redact PII with Presidio
    AttAgent->>AttAgent: Save redacted text files
    AttAgent-->>Workflow: StageResult(success, data, timing)
    
    Note over Workflow: Stage 2: Application
    Workflow->>AppAgent: analyze_application(wai_number)
    AppAgent->>AppAgent: Extract PDF with Docling
    AppAgent->>AppAgent: Analyze with LLM
    AppAgent->>AppAgent: Validate with JSON schema
    AppAgent->>AppAgent: Save application JSON
    AppAgent-->>Workflow: StageResult(success, data, timing)
    
    Note over Workflow: Stage 3: Recommendations
    Workflow->>RecAgent: analyze_recommendations(wai_number)
    RecAgent->>RecAgent: Find first 2 text files
    RecAgent->>RecAgent: Load criteria
    RecAgent->>RecAgent: Analyze with LLM
    RecAgent->>RecAgent: Save recommendation JSON
    RecAgent-->>Workflow: StageResult(success, data, timing)
    
    Note over Workflow: Stage 4: Academic
    Workflow->>AcaAgent: analyze_academic_profile(wai_number)
    AcaAgent->>AcaAgent: Find 3rd text file (resume)
    AcaAgent->>AcaAgent: Analyze with LLM
    AcaAgent->>AcaAgent: Save academic JSON
    AcaAgent-->>Workflow: StageResult(success, data, timing)
    
    Note over Workflow: Stage 5: Essays
    Workflow->>EssAgent: analyze_essays(wai_number)
    EssAgent->>EssAgent: Find files 4 & 5
    EssAgent->>EssAgent: Load criteria
    EssAgent->>EssAgent: Analyze with LLM
    EssAgent->>EssAgent: Save essay JSON
    EssAgent-->>Workflow: StageResult(success, data, timing)
    
    Workflow-->>User: ApplicantResult(success, stages, timing)
    
    Note over User,SumAgent: After all applicants processed
    
    User->>Workflow: process_all_applicants()
    Workflow->>SumAgent: generate_summary_csv()
    SumAgent->>SumAgent: Collect all scores
    SumAgent->>SumAgent: Calculate final scores
    SumAgent->>SumAgent: Generate CSV
    SumAgent->>SumAgent: Calculate statistics
    SumAgent->>SumAgent: Render template
    SumAgent-->>Workflow: Summary results
    Workflow-->>User: Complete results
```

## Batch Processing Flow (with Parallel Execution)

```mermaid
flowchart TD
    START([Start Workflow]) --> INIT[Initialize Workflow<br/>Load Configuration]
    INIT --> DISCOVER[Discover Applicants<br/>from Scholarship Folder]
    DISCOVER --> LIMIT{Apply<br/>Max Limit?}
    LIMIT -->|Yes| SLICE[Slice to max_applicants]
    LIMIT -->|No| LOOP
    SLICE --> LOOP
    
    LOOP[For Each Applicant] --> PHASE1[Phase 1: Sequential Preprocessing]
    
    PHASE1 --> STAGE1{Skip<br/>Attachments?}
    STAGE1 -->|No| ATT[Process Attachments<br/>Redact PII]
    STAGE1 -->|Yes| STAGE2
    ATT --> STAGE2
    
    STAGE2{Skip<br/>Application?} -->|No| APP[Analyze Application<br/>Extract Info]
    STAGE2 -->|Yes| PHASE2
    APP --> PHASE2
    
    PHASE2[Phase 2: Parallel Analysis] --> PARALLEL{Parallel<br/>Mode?}
    
    PARALLEL -->|Yes| THREAD[ThreadPoolExecutor<br/>max_workers=3]
    PARALLEL -->|No| SEQ[Sequential Execution]
    
    THREAD --> REC_P[Analyze Recommendations]
    THREAD --> ACA_P[Analyze Academic]
    THREAD --> ESS_P[Analyze Essays]
    
    REC_P --> WAIT[Wait for All<br/>to Complete]
    ACA_P --> WAIT
    ESS_P --> WAIT
    
    SEQ --> REC_S[Analyze Recommendations]
    REC_S --> ACA_S[Analyze Academic]
    ACA_S --> ESS_S[Analyze Essays]
    ESS_S --> COLLECT
    
    WAIT --> COLLECT[Collect Stage Results]
    
    COLLECT --> CHECK{All Stages<br/>Successful?}
    CHECK -->|Yes| SUCCESS[Mark Success]
    CHECK -->|No| FAIL[Mark Failed]
    SUCCESS --> NEXT
    FAIL --> NEXT
    
    NEXT{More<br/>Applicants?} -->|Yes| LOOP
    NEXT -->|No| SUMMARY
    
    SUMMARY{Skip<br/>Summary?} -->|No| SUM[Generate Summary<br/>CSV & Statistics]
    SUMMARY -->|Yes| RESULTS
    SUM --> RESULTS
    
    RESULTS[Compile Results<br/>Calculate Totals] --> END([Return Results])
    
    style START fill:#4A90E2,stroke:#2E5C8A,color:#fff
    style END fill:#4A90E2,stroke:#2E5C8A,color:#fff
    style PHASE1 fill:#FFD700,stroke:#B8860B,color:#000
    style PHASE2 fill:#FFD700,stroke:#B8860B,color:#000
    style ATT fill:#50C878,stroke:#2E7D4E,color:#fff
    style APP fill:#50C878,stroke:#2E7D4E,color:#fff
    style THREAD fill:#9370DB,stroke:#4B0082,color:#fff
    style REC_P fill:#50C878,stroke:#2E7D4E,color:#fff
    style ACA_P fill:#50C878,stroke:#2E7D4E,color:#fff
    style ESS_P fill:#50C878,stroke:#2E7D4E,color:#fff
    style REC_S fill:#50C878,stroke:#2E7D4E,color:#fff
    style ACA_S fill:#50C878,stroke:#2E7D4E,color:#fff
    style ESS_S fill:#50C878,stroke:#2E7D4E,color:#fff
    style SUM fill:#50C878,stroke:#2E7D4E,color:#fff
    style SUCCESS fill:#90EE90,stroke:#228B22,color:#000
    style FAIL fill:#FFB6C1,stroke:#DC143C,color:#000
```

## Data Flow Diagram

```mermaid
graph LR
    subgraph "Input Files"
        PDF[Application PDF]
        ATT1[Attachment 1<br/>Recommendation]
        ATT2[Attachment 2<br/>Recommendation]
        ATT3[Attachment 3<br/>Resume/CV]
        ATT4[Attachment 4<br/>Essay 1]
        ATT5[Attachment 5<br/>Essay 2]
    end
    
    subgraph "Stage 1: Attachments"
        DOCLING1[Docling<br/>PDF→Text]
        PRESIDIO[Presidio<br/>PII Redaction]
        TXT1[Redacted Text 1]
        TXT2[Redacted Text 2]
        TXT3[Redacted Text 3]
        TXT4[Redacted Text 4]
        TXT5[Redacted Text 5]
    end
    
    subgraph "Stage 2: Application"
        DOCLING2[Docling<br/>PDF→Text]
        LLM1[LLM Analysis<br/>Ollama]
        SCHEMA1[JSON Schema<br/>Validation]
        JSON1[Application JSON<br/>Score: 0-100]
    end
    
    subgraph "Stage 3: Recommendations"
        CRITERIA1[Load Criteria<br/>recommendation_criteria.txt]
        LLM2[LLM Analysis<br/>Ollama]
        SCHEMA2[JSON Schema<br/>Validation]
        JSON2[Recommendation JSON<br/>Score: 0-100]
    end
    
    subgraph "Stage 4: Academic"
        LLM3[LLM Analysis<br/>Ollama]
        SCHEMA3[JSON Schema<br/>Validation]
        JSON3[Academic JSON<br/>Score: 0-100]
    end
    
    subgraph "Stage 5: Essays"
        CRITERIA2[Load Criteria<br/>essay_criteria.txt]
        LLM4[LLM Analysis<br/>Ollama]
        SCHEMA4[JSON Schema<br/>Validation]
        JSON4[Essay JSON<br/>Score: 0-100]
    end
    
    subgraph "Stage 6: Summary"
        COLLECT[Collect All Scores]
        CALC[Calculate<br/>Weighted Final Score]
        RANK[Rank Applicants]
        CSVOUT[Summary CSV]
        STATS[Statistics Report<br/>from Template]
    end
    
    ATT1 --> DOCLING1
    ATT2 --> DOCLING1
    ATT3 --> DOCLING1
    ATT4 --> DOCLING1
    ATT5 --> DOCLING1
    DOCLING1 --> PRESIDIO
    PRESIDIO --> TXT1
    PRESIDIO --> TXT2
    PRESIDIO --> TXT3
    PRESIDIO --> TXT4
    PRESIDIO --> TXT5
    
    PDF --> DOCLING2
    DOCLING2 --> LLM1
    LLM1 --> SCHEMA1
    SCHEMA1 --> JSON1
    
    TXT1 --> CRITERIA1
    TXT2 --> CRITERIA1
    CRITERIA1 --> LLM2
    LLM2 --> SCHEMA2
    SCHEMA2 --> JSON2
    
    TXT3 --> LLM3
    LLM3 --> SCHEMA3
    SCHEMA3 --> JSON3
    
    TXT4 --> CRITERIA2
    TXT5 --> CRITERIA2
    CRITERIA2 --> LLM4
    LLM4 --> SCHEMA4
    SCHEMA4 --> JSON4
    
    JSON1 --> COLLECT
    JSON2 --> COLLECT
    JSON3 --> COLLECT
    JSON4 --> COLLECT
    COLLECT --> CALC
    CALC --> RANK
    RANK --> CSVOUT
    RANK --> STATS
    
    style DOCLING1 fill:#FFD700,stroke:#B8860B,color:#000
    style DOCLING2 fill:#FFD700,stroke:#B8860B,color:#000
    style PRESIDIO fill:#FF6347,stroke:#8B0000,color:#fff
    style LLM1 fill:#9370DB,stroke:#4B0082,color:#fff
    style LLM2 fill:#9370DB,stroke:#4B0082,color:#fff
    style LLM3 fill:#9370DB,stroke:#4B0082,color:#fff
    style LLM4 fill:#9370DB,stroke:#4B0082,color:#fff
```

## Error Handling Flow

```mermaid
flowchart TD
    STAGE[Execute Stage] --> TRY{Try Execute}
    TRY -->|Success| TIME[Record Duration]
    TRY -->|Exception| CATCH[Catch Exception]
    
    TIME --> RESULT1[Create StageResult<br/>success=True<br/>data=result<br/>duration=time]
    
    CATCH --> LOG[Log Error]
    LOG --> RESULT2[Create StageResult<br/>success=False<br/>error=message<br/>duration=time]
    
    RESULT1 --> CONTINUE[Continue to Next Stage]
    RESULT2 --> CONTINUE
    
    CONTINUE --> CHECK{More Stages?}
    CHECK -->|Yes| STAGE
    CHECK -->|No| FINAL[Create ApplicantResult<br/>success=all_stages_ok]
    
    FINAL --> RETURN[Return Result]
    
    style CATCH fill:#FFB6C1,stroke:#DC143C,color:#000
    style LOG fill:#FFB6C1,stroke:#DC143C,color:#000
    style RESULT2 fill:#FFB6C1,stroke:#DC143C,color:#000
    style RESULT1 fill:#90EE90,stroke:#228B22,color:#000
    style TIME fill:#90EE90,stroke:#228B22,color:#000
```

## Configuration and Weights

```mermaid
graph TB
    subgraph "Configuration"
        AGENTS[agents.json]
        WEIGHTS[Agent Weights]
        ORDER[Processing Order]
        CRITERIA[Criteria Files]
    end
    
    subgraph "Score Calculation"
        APP_SCORE[Application Score<br/>Weight: 20%]
        REC_SCORE[Recommendation Score<br/>Weight: 25%]
        ACA_SCORE[Academic Score<br/>Weight: 25%]
        ESS_SCORE[Essay Score<br/>Weight: 30%]
        FINAL[Final Weighted Score<br/>0-100]
    end
    
    AGENTS --> WEIGHTS
    WEIGHTS --> APP_SCORE
    WEIGHTS --> REC_SCORE
    WEIGHTS --> ACA_SCORE
    WEIGHTS --> ESS_SCORE
    
    APP_SCORE --> FINAL
    REC_SCORE --> FINAL
    ACA_SCORE --> FINAL
    ESS_SCORE --> FINAL
    
    AGENTS --> ORDER
    AGENTS --> CRITERIA
    
    style FINAL fill:#FFD700,stroke:#B8860B,color:#000
```

## Usage Patterns

```mermaid
graph TD
    subgraph "Pattern 1: Single Applicant"
        P1[workflow.process_applicant<br/>'75179']
        P1 --> R1[ApplicantResult<br/>5 stages<br/>timing info]
    end
    
    subgraph "Pattern 2: Batch Processing"
        P2[workflow.process_all_applicants<br/>max_applicants=10]
        P2 --> R2[Batch Results<br/>10 applicants<br/>summary CSV<br/>statistics]
    end
    
    subgraph "Pattern 3: Resume Processing"
        P3["workflow.process_all_applicants<br/>skip_stages=attachments"]
        P3 --> R3[Batch Results<br/>skipped stage 1<br/>faster execution]
    end
    
    subgraph "Pattern 4: Specific Applicants"
        P4["workflow.process_all_applicants<br/>wai_numbers=specific list"]
        P4 --> R4[Batch Results<br/>2 specific applicants]
    end
    
    style P1 fill:#4A90E2,stroke:#2E5C8A,color:#fff
    style P2 fill:#4A90E2,stroke:#2E5C8A,color:#fff
    style P3 fill:#4A90E2,stroke:#2E5C8A,color:#fff
    style P4 fill:#4A90E2,stroke:#2E5C8A,color:#fff
```
