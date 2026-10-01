# Threshold Estimation Implementation - Detailed Explanation

## Source: Lecluyse & Meddis (2009)

### **Exact Quote from Paper:**

> "The threshold is estimated at the end of the run. All stimulus levels from trial 1 (defined above and see Fig. 1) onwards are included in the estimate of the threshold... A psychometric function as described in Eq. 1 is fitted to the responses using a least-squares, best-fit procedure, with θ and k as free parameters."

### **The Psychometric Function (Equation 1):**

```
p(L) = 1 / (1 + exp(-k(L - θ)))
```

Where:
- **p(L)** = proportion of "yes" responses at stimulus level L
- **L** = stimulus level (in dB SPL)
- **k** = slope parameter of the psychometric function
- **θ** (theta) = threshold (in dB SPL) - the level where p(L) = 0.5

This is the **logistic function** (also called sigmoid or Boltzmann function).

---

## **Conceptual Understanding**

### **What is a Psychometric Function?**

A psychometric function describes the relationship between stimulus intensity and the probability of detection. For hearing thresholds:

- At very low levels: p(L) ≈ 0 (never heard)
- At threshold (θ): p(L) = 0.5 (heard 50% of the time)
- At high levels: p(L) ≈ 1 (always heard)

### **What is the Slope Parameter k?**

The slope parameter **k** determines how steep the transition is:

- **k = 0.5**: Shallow slope (typical for normal hearing)
  - Wide range of levels where detection is uncertain
  - More variability in responses
  
- **k = 1.0**: Steep slope (typical for impaired hearing)
  - Narrow transition from "never" to "always" detected
  - More consistent responses near threshold

From the paper:
> "The value of k typically is close to 0.5 for normal hearing... the slope of the psychometric function can be steeper than normal for patients with a moderate hearing impairment."

---

## **Implementation Strategy**

### **Step 1: Collect Data**

During a run, we collect:
- Stimulus levels (L₁, L₂, L₃, ...) in dB
- Responses (yes/no) coded as 1/0
- Only trials from "trial 1" onwards (starting from trial before first reversal)

### **Step 2: Fit the Function**

We need to find the values of **θ** (threshold) and **k** (slope) that best fit our data using **least-squares optimization**.

The objective is to minimize:
```
Σ (observed_response - predicted_response)²
```

Where:
- observed_response = 1 (yes) or 0 (no)
- predicted_response = p(L) from our logistic function

### **Step 3: Use scipy.optimize.curve_fit**

Python's `scipy` library provides `curve_fit` which:
- Takes our logistic function
- Takes our data (levels and responses)
- Finds optimal θ and k parameters
- Uses nonlinear least-squares (Levenberg-Marquardt algorithm)

---

## **Code Implementation**

```python
def fit_psychometric_function(levels_dB, responses):
    """
    Fit logistic psychometric function to threshold data.
    
    Per Lecluyse & Meddis (2009):
    "A psychometric function... is fitted to the responses using a 
    least-squares, best-fit procedure, with θ and k as free parameters."
    
    The psychometric function is:
        p(L) = 1 / (1 + exp(-k(L - θ)))
    
    Where:
        p(L) = probability of "yes" response at level L
        L = stimulus level (dB)
        k = slope parameter (typically 0.5 for normal hearing)
        θ = threshold (dB) where p(L) = 0.5
    
    Args:
        levels_dB: Array of stimulus levels in dB
        responses: Array of binary responses (1 = yes/heard, 0 = no/not heard)
    
    Returns:
        dict with keys:
            'threshold_dB': Estimated threshold (θ)
            'slope_k': Estimated slope parameter (k)
            'success': True if fit converged, False otherwise
            'p_curve': Function to evaluate fitted psychometric curve
    """
    import numpy as np
    from scipy.optimize import curve_fit
    
    # Define logistic psychometric function (Equation 1 from paper)
    def logistic(L, theta, k):
        """
        Logistic psychometric function.
        
        Args:
            L: Stimulus level (dB)
            theta: Threshold parameter
            k: Slope parameter
        
        Returns:
            Probability of "yes" response
        """
        return 1.0 / (1.0 + np.exp(-k * (L - theta)))
    
    # Convert to numpy arrays
    levels_dB = np.array(levels_dB, dtype=float)
    responses = np.array(responses, dtype=float)
    
    # Need at least 3 data points to fit 2 parameters
    if len(levels_dB) < 3:
        return {
            'threshold_dB': np.nan,
            'slope_k': np.nan,
            'success': False,
            'p_curve': None,
            'error': 'Insufficient data points (need >= 3)'
        }
    
    # Check for valid data
    if np.all(responses == 0) or np.all(responses == 1):
        # All same response - cannot fit
        return {
            'threshold_dB': np.nan,
            'slope_k': np.nan,
            'success': False,
            'p_curve': None,
            'error': 'No variation in responses'
        }
    
    try:
        # Initial guesses for parameters
        # theta: midpoint of level range
        # k: 0.5 (typical for normal hearing per paper)
        theta_init = np.median(levels_dB)
        k_init = 0.5
        
        # Fit using least-squares
        # curve_fit finds optimal theta and k to minimize:
        # Σ (observed_response - logistic(L, theta, k))²
        params, covariance = curve_fit(
            logistic,
            levels_dB,
            responses,
            p0=[theta_init, k_init],
            maxfev=10000  # Max iterations
        )
        
        theta_fit, k_fit = params
        
        # Create function for fitted curve
        def p_curve(L):
            return logistic(L, theta_fit, k_fit)
        
        return {
            'threshold_dB': theta_fit,
            'slope_k': k_fit,
            'success': True,
            'p_curve': p_curve,
            'covariance': covariance
        }
        
    except RuntimeError as e:
        # Fit failed to converge
        return {
            'threshold_dB': np.nan,
            'slope_k': np.nan,
            'success': False,
            'p_curve': None,
            'error': f'Fit failed: {str(e)}'
        }
```

---

## **How It Works Step-by-Step**

### **1. Data Preparation**
```python
levels_dB = [-10, -8, -6, -4, -2, 0, 2, 4]
responses = [0, 0, 0, 1, 0, 1, 1, 1]
```

### **2. Initial Guess**
- θ_init = median(levels) = -1 dB
- k_init = 0.5 (from literature)

### **3. Optimization Loop**
The `curve_fit` function iteratively adjusts θ and k to minimize error:

Iteration 1: Try θ = -1, k = 0.5 → calculate error
Iteration 2: Try θ = -0.8, k = 0.48 → calculate error (better!)
Iteration 3: Try θ = -0.6, k = 0.52 → calculate error
...
Continue until error stops decreasing

### **4. Result**
Final best-fit parameters, e.g.:
- θ = -0.5 dB (threshold where 50% detection occurs)
- k = 0.48 (slope parameter)

---

## **Integration into Paradigm**

The function will be called at the end of each config run:

```python
# In adaptive_paradigm.py, when config ends:
if self.end_config:
    # Fit psychometric function to estimate threshold
    threshold_result = self.fit_psychometric_function(
        self.threshold_levels_dB,
        self.threshold_responses
    )
    
    if threshold_result['success']:
        threshold_dB = threshold_result['threshold_dB']
        slope_k = threshold_result['slope_k']
        
        if self.verbose:
            print(f"\n*** THRESHOLD ESTIMATE ***")
            print(f"  Threshold: {threshold_dB:.2f} dB")
            print(f"  Slope (k): {slope_k:.3f}")
    
    # Add to logged data
    self.threshold_dB = threshold_dB
    self.slope_k = slope_k
```

---

## **Expected Behavior Examples**

### **Example 1: Normal Hearing (k ≈ 0.5)**
```
Level (dB): -10, -8, -6, -4, -2,  0,  2,  4,  6
Response:     0,  0,  0,  1,  0,  1,  1,  1,  1
                              ↑ threshold ≈ -2 dB
```

### **Example 2: Impaired Hearing (k ≈ 1.0)**
```
Level (dB): 60, 62, 64, 66, 68, 70, 72, 74, 76
Response:     0,  0,  0,  0,  1,  1,  1,  1,  1
                              ↑ threshold ≈ 68 dB (steep transition)
```

---

## **Validation**

From the paper, for normal hearing:
- **k should be ≈ 0.48 - 0.62** (Figure 5)
- **θ should match behavioral threshold** (within ~2 dB)

Our implementation will produce these values when fit to real data.
