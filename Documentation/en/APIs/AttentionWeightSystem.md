# User Attention Weight System Design

## Overview

The User Attention Weight System is a core component of ByenatOS that analyzes user HiNATA behavior patterns to quantify users' real attention to different content, and integrates these weight information into the PSP iteration mechanism to ensure the operating system can accurately understand and respond to users' real needs.

## System Architecture

### Overall Design Principles

1. **Behavior-Driven Weights** - Calculate attention weights based on users' actual behaviors
2. **Multi-Dimensional Assessment** - Analyze user attention from multiple dimensions including frequency, depth, time, and revisits
3. **Real-Time Updates** - Adjust weights in real-time as new HiNATA data streams in
4. **PSP Integration** - Directly apply weight information to PSP iteration and decision-making

### Core Components

```
HiNATA Data Stream → Attention Pattern Analysis → Weight Calculation → PSP Weight Fusion → Personalized Experience Optimization
```

## Attention Weight Calculation Mechanism

### Weight Factor Definitions

#### 1. Highlight Frequency Weight (30%)
**Definition**: Frequency of users highlighting similar content
**Calculation Logic**:
```python
def calculate_highlight_frequency_weight(similarity_count):
    """
    similarity_count: Number of similar highlights
    Return value: 0.1 - 1.0
    """
    if similarity_count <= 1:
        return 0.1  # First-time attention
    elif similarity_count <= 3:
        return 0.4  # Initial attention
    elif similarity_count <= 5:
        return 0.7  # Sustained attention
    else:
        return 1.0  # Deep attention
```

#### 2. Note Density Weight (25%)
**Definition**: Quantity and quality of notes added by users under the same topic or address
**Calculation Logic**:
```python
def calculate_note_density_weight(note_count, avg_note_length):
    """
    note_count: Number of notes at the same address
    avg_note_length: Average note length
    Return value: 0.2 - 1.0
    """
    base_weight = min(note_count / 5.0, 1.0)  # Based on quantity
    quality_bonus = min(avg_note_length / 200.0, 0.3)  # Based on quality
    
    return max(0.2, base_weight + quality_bonus)
```

#### 3. Address Revisit Weight (30%)
**Definition**: Users' repeated visits and operations on the same resource address
**Calculation Logic**:
```python
def calculate_revisit_weight(visit_count, time_span_days):
    """
    visit_count: Number of visits
    time_span_days: Time span (days)
    Return value: 0.1 - 1.0
    """
    frequency_weight = min(visit_count / 6.0, 1.0)
    persistence_bonus = min(time_span_days / 30.0, 0.2)
    
    return max(0.1, frequency_weight + persistence_bonus)
```

#### 4. Time Investment Weight (15%)
**Definition**: Total time users invest in related topics
**Calculation Logic**:
```python
def calculate_time_investment_weight(total_seconds):
    """
    total_seconds: Total investment time (seconds)
    Return value: 0.1 - 1.0
    """
    # Use logarithmic function to avoid excessive weight from long time periods
    normalized_time = math.log(total_seconds + 1) / math.log(3600)  # Based on 1 hour
    return min(max(0.1, normalized_time), 1.0)
```

### Comprehensive Weight Calculation

```python
def calculate_comprehensive_attention_weight(metrics):
    """Calculate comprehensive attention weight"""
    highlight_weight = calculate_highlight_frequency_weight(metrics['highlight_frequency'])
    note_weight = calculate_note_density_weight(metrics['note_count'], metrics['avg_note_length'])
    revisit_weight = calculate_revisit_weight(metrics['address_revisit'], metrics['time_span'])
    time_weight = calculate_time_investment_weight(metrics['time_investment'])
    
    # Weighted average
    attention_weight = (
        highlight_weight * 0.30 +
        note_weight * 0.25 +
        revisit_weight * 0.30 +
        time_weight * 0.15
    )
    
    # Apply interaction depth adjustment factor
    depth_multiplier = get_depth_multiplier(metrics['interaction_depth'])
    final_weight = min(attention_weight * depth_multiplier, 1.0)
    
    return final_weight

def get_depth_multiplier(interaction_depth):
    """Get adjustment factor based on interaction depth"""
    multipliers = {
        'low': 0.8,
        'medium': 1.0,
        'high': 1.2
    }
    return multipliers.get(interaction_depth, 1.0)
```

## Operating System Level Integration Mechanism

### 1. Real-Time Weight Update Service

```python
class AttentionWeightService:
    def __init__(self):
        self.weight_calculator = AttentionWeightCalculator()
        self.historical_analyzer = HistoricalDataAnalyzer()
        self.psp_integrator = PSPIntegrator()
        
    def process_hinata_stream(self, hinata_record):
        """Process individual HiNATA record"""
        # 1. Calculate attention weight
        attention_weight = self.weight_calculator.calculate(
            hinata_record, 
            self.historical_analyzer.get_context(hinata_record['user_id'])
        )
        
        # 2. Update record
        hinata_record['attention_weight'] = attention_weight
        
        # 3. Trigger PSP update
        self.psp_integrator.update_with_attention_weight(hinata_record)
        
        # 4. Notify related services
        self.notify_attention_update(hinata_record)
        
        return hinata_record
```

### 2. Historical Data Analyzer

```python
class HistoricalDataAnalyzer:
    def __init__(self):
        self.data_store = VectorDatabase()
        self.cache = LRUCache(maxsize=1000)
        
    def get_context(self, user_id, time_window='30d'):
        """Get user historical context"""
        cache_key = f"{user_id}_{time_window}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Query historical data
        historical_data = self.data_store.query_user_history(
            user_id=user_id,
            time_range=time_window,
            include_fields=['highlight', 'note', 'address', 'timestamp', 'attention_weight']
        )
        
        # Build context
        context = self.build_attention_context(historical_data)
        self.cache[cache_key] = context
        
        return context
    
    def build_attention_context(self, historical_data):
        """Build attention context"""
        return {
            'highlight_patterns': self.extract_highlight_patterns(historical_data),
            'address_frequencies': self.calculate_address_frequencies(historical_data),
            'topic_time_investment': self.calculate_topic_time_investment(historical_data),
            'interaction_trends': self.analyze_interaction_trends(historical_data)
        }
```

### 3. PSP Weight Integrator

```python
class PSPIntegrator:
    def __init__(self):
        self.psp_manager = PSPManager()
        self.weight_aggregator = WeightAggregator()
        
    def update_with_attention_weight(self, hinata_record):
        """Update PSP based on attention weight"""
        user_id = hinata_record['user_id']
        attention_weight = hinata_record['attention_weight']
        
        # Get current PSP
        current_psp = self.psp_manager.get_user_psp(user_id)
        
        # Extract intent
        intent = extract_intent_from_hinata(hinata_record)
        intent['attention_weight'] = attention_weight
        
        # Match with PSP components
        matches = match_intent_with_psp(intent, current_psp)
        
        # Update PSP based on attention weight
        updated_psp = self.apply_attention_weighted_update(matches, current_psp)
        
        # Save updated PSP
        self.psp_manager.update_user_psp(user_id, updated_psp)
        
    def apply_attention_weighted_update(self, matches, current_psp):
        """Apply attention-weighted PSP update"""
        # Sort by attention weight
        weighted_matches = sorted(
            matches, 
            key=lambda x: x['intent'].get('attention_weight', 0), 
            reverse=True
        )
        
        for match in weighted_matches:
            attention_weight = match['intent']['attention_weight']
            
            if attention_weight > 0.7:  # High-weight content
                # Strong update, increase influence
                self.apply_strong_update(match, current_psp)
            elif attention_weight > 0.4:  # Medium-weight content
                # Standard update
                self.apply_standard_update(match, current_psp)
            else:  # Low-weight content
                # Light update, avoid noise
                self.apply_light_update(match, current_psp)
        
        return current_psp
```

## System Performance Optimization

### 1. Caching Strategy

```python
class AttentionWeightCache:
    def __init__(self):
        self.redis_client = redis.Redis()
        self.local_cache = LRUCache(maxsize=500)
        
    def get_cached_weight(self, hinata_hash):
        """Get cached weight"""
        # First check local cache
        if hinata_hash in self.local_cache:
            return self.local_cache[hinata_hash]
        
        # Check Redis cache
        cached_data = self.redis_client.get(f"attention_weight:{hinata_hash}")
        if cached_data:
            weight_data = json.loads(cached_data)
            self.local_cache[hinata_hash] = weight_data
            return weight_data
        
        return None
    
    def cache_weight(self, hinata_hash, weight_data, ttl=3600):
        """Cache weight data"""
        # Local cache
        self.local_cache[hinata_hash] = weight_data
        
        # Redis cache
        self.redis_client.setex(
            f"attention_weight:{hinata_hash}",
            ttl,
            json.dumps(weight_data)
        )
```

### 2. Batch Processing

```python
class BatchAttentionProcessor:
    def __init__(self, batch_size=50):
        self.batch_size = batch_size
        self.pending_records = []
        
    def add_record(self, hinata_record):
        """Add record to batch processing queue"""
        self.pending_records.append(hinata_record)
        
        if len(self.pending_records) >= self.batch_size:
            self.process_batch()
    
    def process_batch(self):
        """Process records in batch"""
        if not self.pending_records:
            return
        
        # Group by user
        user_groups = group_by_user(self.pending_records)
        
        # Process each user's data in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for user_id, records in user_groups.items():
                future = executor.submit(self.process_user_batch, user_id, records)
                futures.append(future)
            
            # Wait for all tasks to complete
            for future in futures:
                future.result()
        
        # Clear queue
        self.pending_records.clear()
```

## Application Scenarios

### Scenario 1: Technology Learning Tracking

```python
# User's attention evolution for "Machine Learning" topic
timeline = [
    {
        "day": 1,
        "hinata_count": 2,
        "attention_weight": 0.3,
        "action": "Initial contact, simple highlight"
    },
    {
        "day": 3,
        "hinata_count": 5,
        "attention_weight": 0.6,
        "action": "Deep reading, adding detailed notes"
    },
    {
        "day": 7,
        "hinata_count": 8,
        "attention_weight": 0.8,
        "action": "Revisiting resources, multiple highlights of same concept"
    },
    {
        "day": 14,
        "hinata_count": 12,
        "attention_weight": 0.95,
        "action": "Continuous learning, cross-resource associative thinking"
    }
]

# PSP evolution result
psp_evolution = {
    "core_interest": "Machine Learning",
    "weight_progression": [0.3, 0.6, 0.8, 0.95],
    "psp_influence": "Developed from peripheral interest to core focus",
    "system_adaptation": "Prioritize related content, adjust workflow"
}
```

### Scenario 2: Project Research Depth

```python
# User's attention distribution when researching "Blockchain Technology"
attention_analysis = {
    "total_hinata_count": 25,
    "unique_sources": 8,
    "time_span_days": 21,
    "metrics": {
        "highlight_frequency": 15,  # Similar concepts highlighted 15 times
        "note_count": 12,           # 12 detailed notes
        "address_revisit": 6,       # Revisited 6 key resources
        "time_investment": 3600,    # Invested 1 hour in deep thinking
        "interaction_depth": "high"
    },
    "calculated_weight": 0.92,
    "psp_impact": "Became core working memory component"
}
```

## Monitoring and Tuning

### Weight Quality Assessment

```python
class AttentionWeightQualityMonitor:
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        
    def evaluate_weight_quality(self, user_id, time_period='7d'):
        """Evaluate weight quality"""
        metrics = {
            'weight_distribution': self.analyze_weight_distribution(user_id, time_period),
            'psp_correlation': self.measure_psp_correlation(user_id, time_period),
            'user_satisfaction': self.get_user_feedback_score(user_id, time_period),
            'prediction_accuracy': self.measure_prediction_accuracy(user_id, time_period)
        }
        
        return self.calculate_quality_score(metrics)
    
    def suggest_optimizations(self, quality_metrics):
        """Suggest optimization strategies"""
        suggestions = []
        
        if quality_metrics['weight_distribution']['variance'] > 0.8:
            suggestions.append("Adjust weight factor ratios to reduce variance")
        
        if quality_metrics['psp_correlation'] < 0.7:
            suggestions.append("Optimize PSP integration algorithm")
        
        if quality_metrics['user_satisfaction'] < 0.8:
            suggestions.append("Increase user feedback weight")
        
        return suggestions
```

## Summary

The User Attention Weight System ensures ByenatOS can accurately understand users' real attention through the following mechanisms:

### Core Advantages

1. **Multi-Dimensional Analysis** - Comprehensively considers factors like frequency, depth, time, and revisits
2. **Real-Time Updates** - Adjusts weights and PSP in real-time as user behavior changes
3. **PSP Integration** - Directly influences the operating system's personalized decision-making
4. **Performance Optimization** - Ensures system efficiency through caching and batch processing

### System Effects

- **Improve PSP Accuracy** - Adjust personal system prompts based on real attention levels
- **Optimize Resource Allocation** - Invest computing resources in content users truly care about
- **Enhance User Experience** - Provide more precise personalized services
- **Reduce Information Noise** - Filter low-weight information, highlight important content

This attention weight system is the key infrastructure for ByenatOS to achieve truly personalized operating system experiences.